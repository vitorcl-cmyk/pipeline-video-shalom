"""Scraper periódico de shalomconsultoria.com.br -> JSON estático.

Gera o arquivo consumido pelo widget de vitrine (`/showcase-widget`), com um
registro por imóvel: foto, bairro, tipo, valor e link. Pensado pra rodar via
cron/systemd timer (ver README.md deste diretório) e sobrescrever sempre o
mesmo arquivo de saída.

IMPORTANTE — seletores de calibração:
Este script foi escrito sem acesso ao HTML ao vivo do site (bloqueado no
ambiente onde foi desenvolvido). Os seletores CSS abaixo, em `SELECTORS`,
são um ponto de partida a partir de padrões comuns de sites de imobiliária
e PRECISAM ser conferidos/ajustados contra o HTML real antes do primeiro
uso em produção — abra a página de listagem no navegador, inspecione um
card de imóvel e corrija os seletores correspondentes. O resto do pipeline
(paginação, parsing de valor, escrita atômica do JSON) não depende do
site específico.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("scrape_shalom")

BASE_URL = "https://www.shalomconsultoria.com.br"
LISTINGS_PATH = "/imoveis"  # AJUSTAR: caminho real da listagem de imóveis
USER_AGENT = "ShalomShowcaseBot/1.0 (+https://shalomconsultoria.com.br; vitrine de imoveis)"
REQUEST_TIMEOUT = 20
DEFAULT_PAUSE_SECONDS = 1.5  # intervalo entre requisições, por educação com o servidor

# AJUSTAR: seletores CSS conforme o HTML real do site.
SELECTORS = {
    "card": "div.imovel-card, article.property-card, li.imovel-item",
    "title": ".imovel-titulo, .property-title, h2, h3",
    "photo": "img",
    "bairro": ".imovel-bairro, .property-neighborhood",
    "tipo": ".imovel-tipo, .property-type",
    "valor": ".imovel-valor, .property-price",
    "link": "a",
    "next_page": "a.next, a[rel=next]",
}

VALOR_RE = re.compile(r"[\d.,]+")


@dataclass
class Listing:
    id: str
    title: str | None
    photo: str | None
    bairro: str | None
    tipo: str | None
    valor: float | None
    valor_formatado: str | None
    link: str


def parse_valor(text: str | None) -> tuple[float | None, str | None]:
    """Converte um texto de preço em pt-BR (ex.: 'R$ 850.000,00') pra float,
    mantendo o texto original formatado como fallback de exibição."""
    if not text:
        return None, None
    text = text.strip()
    match = VALOR_RE.search(text)
    if not match:
        return None, text
    raw = match.group(0).replace(".", "").replace(",", ".")
    try:
        return float(raw), text
    except ValueError:
        return None, text


def make_id(link: str) -> str:
    slug = link.rstrip("/").rsplit("/", 1)[-1]
    return slug or str(abs(hash(link)))


def fetch(session: requests.Session, url: str) -> BeautifulSoup:
    resp = session.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def extract_listing(card, base_url: str) -> Listing | None:
    link_el = card.select_one(SELECTORS["link"])
    if not link_el or not link_el.get("href"):
        return None
    link = urljoin(base_url, link_el["href"])

    photo_el = card.select_one(SELECTORS["photo"])
    photo = None
    if photo_el:
        photo = photo_el.get("data-src") or photo_el.get("src")
        if photo:
            photo = urljoin(base_url, photo)

    title_el = card.select_one(SELECTORS["title"])
    bairro_el = card.select_one(SELECTORS["bairro"])
    tipo_el = card.select_one(SELECTORS["tipo"])
    valor_el = card.select_one(SELECTORS["valor"])

    valor, valor_formatado = parse_valor(valor_el.get_text() if valor_el else None)

    return Listing(
        id=make_id(link),
        title=title_el.get_text(strip=True) if title_el else None,
        photo=photo,
        bairro=bairro_el.get_text(strip=True) if bairro_el else None,
        tipo=tipo_el.get_text(strip=True) if tipo_el else None,
        valor=valor,
        valor_formatado=valor_formatado,
        link=link,
    )


def scrape(base_url: str, max_pages: int, pause_seconds: float) -> list[Listing]:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    listings: list[Listing] = []
    seen_ids: set[str] = set()
    url = urljoin(base_url, LISTINGS_PATH)
    page = 1

    while url and page <= max_pages:
        logger.info("Página %d: %s", page, url)
        soup = fetch(session, url)

        cards = soup.select(SELECTORS["card"])
        if not cards:
            logger.warning("Nenhum card encontrado com o seletor %r — confira SELECTORS", SELECTORS["card"])
            break

        for card in cards:
            listing = extract_listing(card, base_url)
            if listing and listing.id not in seen_ids:
                seen_ids.add(listing.id)
                listings.append(listing)

        next_el = soup.select_one(SELECTORS["next_page"])
        url = urljoin(base_url, next_el["href"]) if next_el and next_el.get("href") else None
        page += 1

        if url:
            time.sleep(pause_seconds)

    return listings


def write_output(listings: list[Listing], output_path: Path, source: str) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "count": len(listings),
        "listings": [asdict(item) for item in listings],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(output_path)  # escrita atômica -- evita servir JSON parcial


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=BASE_URL, help="URL base do site (default: %(default)s)")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "data" / "listings.json")
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--pause", type=float, default=DEFAULT_PAUSE_SECONDS, help="segundos entre requisições")
    args = parser.parse_args()

    try:
        listings = scrape(args.base_url, args.max_pages, args.pause)
    except requests.RequestException:
        logger.exception("Falha ao acessar %s", args.base_url)
        return 1

    if not listings:
        logger.error("Nenhum imóvel extraído — verifique SELECTORS antes de sobrescrever o JSON de produção")
        return 1

    write_output(listings, args.output, args.base_url)
    logger.info("%d imóveis salvos em %s", len(listings), args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
