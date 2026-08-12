"""
Consulta cadastral e societária de CNPJ usando APIs públicas gratuitas.

Fonte primária: BrasilAPI (https://brasilapi.com.br) — sem necessidade de token.
Fallback: ReceitaWS (https://www.receitaws.com.br) — free tier com rate limit baixo.

Isso cobre, do anúncio do Detetive Alude:
- Dados cadastrais da empresa (razão social, situação, CNAE, endereço)
- "Relacionamentos econômicos" parcialmente, via quadro de sócios (QSA)

NÃO cobre (e não há fonte gratuita legítima para isso):
- Score de crédito, protestos, cheques devolvidos
"""
from __future__ import annotations

import httpx

BRASILAPI_URL = "https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
RECEITAWS_URL = "https://www.receitaws.com.br/v1/cnpj/{cnpj}"

TIMEOUT = 10.0


class ConsultaIndisponivel(Exception):
    pass


def _normalizar_brasilapi(data: dict) -> dict:
    socios = [
        {
            "nome": s.get("nome_socio"),
            "qualificacao": s.get("qualificacao_socio"),
            "data_entrada": s.get("data_entrada_sociedade"),
        }
        for s in data.get("qsa", [])
    ]
    return {
        "fonte": "BrasilAPI",
        "razao_social": data.get("razao_social"),
        "nome_fantasia": data.get("nome_fantasia"),
        "situacao_cadastral": data.get("descricao_situacao_cadastral"),
        "data_situacao": data.get("data_situacao_cadastral"),
        "data_abertura": data.get("data_inicio_atividade"),
        "cnae_principal": data.get("cnae_fiscal_descricao"),
        "endereco": {
            "logradouro": data.get("logradouro"),
            "numero": data.get("numero"),
            "bairro": data.get("bairro"),
            "municipio": data.get("municipio"),
            "uf": data.get("uf"),
            "cep": data.get("cep"),
        },
        "capital_social": data.get("capital_social"),
        "socios": socios,
    }


def _normalizar_receitaws(data: dict) -> dict:
    socios = [
        {"nome": s.get("nome"), "qualificacao": s.get("qual"), "data_entrada": None}
        for s in data.get("qsa", [])
    ]
    return {
        "fonte": "ReceitaWS",
        "razao_social": data.get("nome"),
        "nome_fantasia": data.get("fantasia"),
        "situacao_cadastral": data.get("situacao"),
        "data_situacao": data.get("data_situacao"),
        "data_abertura": data.get("abertura"),
        "cnae_principal": data.get("atividade_principal", [{}])[0].get("text"),
        "endereco": {
            "logradouro": data.get("logradouro"),
            "numero": data.get("numero"),
            "bairro": data.get("bairro"),
            "municipio": data.get("municipio"),
            "uf": data.get("uf"),
            "cep": data.get("cep"),
        },
        "capital_social": data.get("capital_social"),
        "socios": socios,
    }


def consultar_cnpj(cnpj_digitos: str) -> dict:
    """Tenta BrasilAPI; se falhar (rede/limite/erro), tenta ReceitaWS."""
    erros = []

    try:
        resp = httpx.get(BRASILAPI_URL.format(cnpj=cnpj_digitos), timeout=TIMEOUT)
        if resp.status_code == 200:
            return _normalizar_brasilapi(resp.json())
        erros.append(f"BrasilAPI status {resp.status_code}")
    except httpx.HTTPError as e:
        erros.append(f"BrasilAPI erro de rede: {e}")

    try:
        resp = httpx.get(RECEITAWS_URL.format(cnpj=cnpj_digitos), timeout=TIMEOUT)
        if resp.status_code == 200 and resp.json().get("status") != "ERROR":
            return _normalizar_receitaws(resp.json())
        erros.append(f"ReceitaWS status {resp.status_code}")
    except httpx.HTTPError as e:
        erros.append(f"ReceitaWS erro de rede: {e}")

    raise ConsultaIndisponivel(
        "Não foi possível consultar o CNPJ em nenhuma fonte gratuita. Detalhes: " + " | ".join(erros)
    )
