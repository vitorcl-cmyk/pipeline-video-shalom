"""Gera o relatório consolidado de uma análise de ficha em texto simples."""
from __future__ import annotations

from app.models import AnaliseFicha
from app.utils import formatar_cnpj, formatar_cpf


def _fmt_doc(documento: str, tipo: str) -> str:
    return formatar_cpf(documento) if tipo == "cpf" else formatar_cnpj(documento)


def _linha(titulo: str) -> str:
    return f"\n{titulo}\n" + "-" * len(titulo)


def gerar_relatorio(analise: AnaliseFicha) -> str:
    doc_fmt = _fmt_doc(analise.documento, analise.tipo_documento)
    linhas = []
    linhas.append("RELATÓRIO DE ANÁLISE DE FICHA — SHALOM CONSULTORIA IMOBILIÁRIA")
    linhas.append(f"Documento: {doc_fmt} ({analise.tipo_documento.upper()})")
    if analise.nome_candidato:
        linhas.append(f"Candidato: {analise.nome_candidato}")
    linhas.append(f"Gerado em: {analise.created_at}")

    linhas.append(_linha("1. IDENTIFICAÇÃO"))
    linhas.append(f"Documento: {doc_fmt}")
    linhas.append(f"Tipo: {analise.tipo_documento.upper()}")

    if analise.tipo_documento == "cnpj":
        cad = analise.dados_cadastrais or {}
        linhas.append(_linha("2. DADOS CADASTRAIS E SOCIETÁRIOS (fonte: " + cad.get("fonte", "não consultado") + ")"))
        if cad:
            linhas.append(f"Razão social: {cad.get('razao_social', 'não informado')}")
            linhas.append(f"Nome fantasia: {cad.get('nome_fantasia', 'não informado')}")
            linhas.append(f"Situação cadastral: {cad.get('situacao_cadastral', 'não informado')}")
            linhas.append(f"Data de abertura: {cad.get('data_abertura', 'não informado')}")
            end = cad.get("endereco", {})
            linhas.append(
                "Endereço: "
                f"{end.get('logradouro', '')}, {end.get('numero', '')} - "
                f"{end.get('bairro', '')}, {end.get('municipio', '')}/{end.get('uf', '')} "
                f"CEP {end.get('cep', '')}"
            )
            socios = cad.get("socios", [])
            linhas.append(f"Sócios/QSA ({len(socios)}):")
            for s in socios:
                linhas.append(f"  - {s.get('nome', 'não informado')} ({s.get('qualificacao', 'não informado')})")
        else:
            linhas.append("Não consultado.")

    linhas.append(_linha("3. SITUAÇÃO JUDICIAL"))
    jud = analise.dados_judiciais or {}
    if jud:
        if jud.get("cobertura_automatica"):
            linhas.append(f"Processos encontrados: {len(jud.get('processos', []))}")
        else:
            linhas.append("Sem cobertura automática nacional gratuita.")
            linhas.append(f"Consulta manual: {jud.get('link_consulta_manual_tjsp', '')}")
            linhas.append(f"Observação: {jud.get('observacao', '')}")
    else:
        linhas.append("Não consultado.")

    linhas.append(_linha("4. DADOS DE SERVIDOR PÚBLICO / SANÇÕES (Portal da Transparência)"))
    serv = analise.dados_servidor or {}
    if serv:
        linhas.append(f"Servidor público federal: {'SIM' if serv.get('eh_servidor_federal') else 'não consta'}")
        linhas.append(f"Sanção/impedimento (CEIS): {'SIM' if serv.get('possui_sancao') else 'não consta'}")
    else:
        linhas.append("Não consultado.")

    linhas.append(_linha("5. CRÉDITO / SPC (dados inseridos manualmente)"))
    spc = analise.dados_spc or {}
    if spc:
        for chave, valor in spc.items():
            linhas.append(f"{chave}: {valor}")
    else:
        linhas.append("Não informado — cole aqui os dados da consulta SPC paga.")

    linhas.append(_linha("6. PARECER FINAL"))
    linhas.append(analise.parecer_final or "Pendente de definição.")
    if analise.observacoes:
        linhas.append(f"Observações: {analise.observacoes}")

    return "\n".join(linhas)
