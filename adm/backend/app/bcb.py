"""Cliente da API pública de séries temporais do Banco Central (SGS).

Usado pra buscar a taxa mensal da poupança e corrigir automaticamente o
valor do depósito caução (Lei do Inquilinato, art. 38: caução em dinheiro
fica em caderneta de poupança). Diferente da "Calculadora do Cidadão"
(um formulário HTML pensado pra uso manual, não pra automação), o SGS é
uma API JSON pública e documentada, sem login:
https://dadosabertos.bcb.gov.br/dataset/195-poupanca---rentabilidade-mensal

Série 195 = poupança, rentabilidade mensal (regra vigente desde 04/05/2012).
Confirmado manualmente ao configurar o servidor de produção (o ambiente de
desenvolvimento não tem acesso à internet pra testar isso aqui).
"""
from datetime import date

import httpx

SGS_POUPANCA_SERIE = 195
SGS_URL = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{SGS_POUPANCA_SERIE}/dados"


class BcbUnavailableError(Exception):
    pass


def fetch_poupanca_rates(data_inicial: date, data_final: date) -> list[dict]:
    """Retorna [{"data": date, "taxa_percentual": float}, ...] com a taxa
    mensal da poupança em cada competência entre data_inicial e data_final
    (inclusive). Lança BcbUnavailableError se a API não responder ou a
    resposta vier num formato inesperado."""
    params = {
        "formato": "json",
        "dataInicial": data_inicial.strftime("%d/%m/%Y"),
        "dataFinal": data_final.strftime("%d/%m/%Y"),
    }
    try:
        resp = httpx.get(SGS_URL, params=params, timeout=15)
        resp.raise_for_status()
        raw = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise BcbUnavailableError(f"não foi possível consultar a API do Banco Central: {exc}") from exc

    result = []
    for item in raw:
        try:
            dia, mes, ano = item["data"].split("/")
            d = date(int(ano), int(mes), int(dia))
            taxa = float(item["valor"].replace(",", "."))
        except (KeyError, ValueError) as exc:
            raise BcbUnavailableError(f"resposta inesperada da API do Banco Central: {exc}") from exc
        result.append({"data": d, "taxa_percentual": taxa})
    return result


def compound_correction(valor_inicial: float, taxas_percentuais: list[float]) -> float:
    """Aplica a correção composta (mês a mês) de uma lista de taxas
    percentuais mensais sobre um valor inicial."""
    valor = valor_inicial
    for taxa in taxas_percentuais:
        valor *= 1 + taxa / 100
    return round(valor, 2)
