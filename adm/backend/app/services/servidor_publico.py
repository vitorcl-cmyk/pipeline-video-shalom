"""
Consulta se um CPF consta como servidor público federal e se há sanções/impedimentos,
via API pública do Portal da Transparência (governo federal).

Requer token gratuito: cadastre-se em
https://api.portaldatransparencia.gov.br/swagger-ui.html -> "Solicitar chave de acesso"
e configure PORTAL_TRANSPARENCIA_TOKEN no .env.

Cobertura real: apenas nível FEDERAL. Servidores estaduais e municipais não têm
API pública unificada — o anúncio do Alude promete os três níveis, mas hoje isso só é
possível de graça para a esfera federal.
"""
from __future__ import annotations

import httpx

from app.config import settings

BASE_URL = "https://api.portaldatransparencia.gov.br/api-de-dados"
TIMEOUT = 10.0


class TokenNaoConfigurado(Exception):
    pass


class ConsultaIndisponivel(Exception):
    pass


def _headers() -> dict:
    token = settings.PORTAL_TRANSPARENCIA_TOKEN
    if not token:
        raise TokenNaoConfigurado(
            "Configure PORTAL_TRANSPARENCIA_TOKEN com uma chave gratuita do Portal da "
            "Transparência (https://api.portaldatransparencia.gov.br)."
        )
    return {"chave-api-dados": token}


def consultar_servidor_federal(cpf_digitos: str) -> dict:
    """Verifica se o CPF consta como servidor público federal ativo."""
    try:
        resp = httpx.get(
            f"{BASE_URL}/servidores",
            params={"cpf": cpf_digitos, "pagina": 1},
            headers=_headers(),
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as e:
        raise ConsultaIndisponivel(f"Erro de rede no Portal da Transparência: {e}") from e

    if resp.status_code != 200:
        raise ConsultaIndisponivel(f"Portal da Transparência retornou status {resp.status_code}")

    registros = resp.json() or []
    return {
        "fonte": "Portal da Transparência (federal)",
        "eh_servidor_federal": len(registros) > 0,
        "registros": registros,
    }


def consultar_sancoes(cpf_ou_cnpj_digitos: str) -> dict:
    """Verifica CEIS/CEPIM/CNEP (empresas e pessoas sancionadas/impedidas)."""
    try:
        resp = httpx.get(
            f"{BASE_URL}/ceis",
            params={"codigoSancionado": cpf_ou_cnpj_digitos, "pagina": 1},
            headers=_headers(),
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as e:
        raise ConsultaIndisponivel(f"Erro de rede no Portal da Transparência: {e}") from e

    if resp.status_code != 200:
        raise ConsultaIndisponivel(f"Portal da Transparência retornou status {resp.status_code}")

    registros = resp.json() or []
    return {
        "fonte": "Portal da Transparência (CEIS - sanções)",
        "possui_sancao": len(registros) > 0,
        "registros": registros,
    }
