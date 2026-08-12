"""
Consulta de processos judiciais.

REALIDADE TÉCNICA (importante ler antes de usar):

A API pública do CNJ (DataJud, https://datajud-wiki.cnj.jus.br) permite pesquisar processos
por NÚMERO do processo, não por CPF/CNPJ da parte, em busca gratuita e nacional unificada.
Não existe hoje uma API pública, gratuita e nacional que faça "CPF -> lista de processos em
todo o Brasil" — é exatamente esse agregador que serviços pagos tipo Detetive Alude vendem,
geralmente reunindo scraping de dezenas de tribunais + acesso a bases pagas (Escavador, Judit
etc.), e nem sempre com 100% de cobertura.

O que dá para fazer de graça, com trabalho manual reduzido (não nesse módulo, mas documentado
aqui para você decidir):
- Tribunais estaduais como o TJSP oferecem consulta pública por CPF/CNPJ da parte em
  https://esaj.tjsp.jus.br/cpopg/open.do — mas exige captcha, o que impede automação
  responsável (contornar captcha viola os termos de uso do tribunal). A consulta manual
  nesse site continua sendo gratuita.
- Existem provedores pagos (Escavador, Judit.io, Predictus) com API oficial que agregam
  vários tribunais — se o volume de consultas justificar, vale comparar o custo por consulta
  desses provedores com o que você paga hoje no Alude.

Este módulo por enquanto:
1. Valida se o documento pode ser usado para consulta manual.
2. Gera o link direto de consulta pública do TJSP (útil pra abrir com um clique e colar o
   CPF/CNPJ, já que captcha impede automação).
3. Deixa um retorno estruturado para, no futuro, plugar uma API paga (Escavador/Judit) sem
   precisar mudar o resto do app.
"""
from __future__ import annotations

ESAJ_TJSP_URL = "https://esaj.tjsp.jus.br/cpopg/open.do"


def gerar_link_consulta_manual_tjsp() -> str:
    return ESAJ_TJSP_URL


def consultar_processos(documento_digitos: str, tipo_documento: str) -> dict:
    """
    Retorno estruturado. Hoje não há fonte gratuita e automatizável nacional, então isso
    devolve o status de "consulta manual pendente" + link direto, em vez de fingir automação
    que não existe.
    """
    return {
        "fonte": "manual (sem API gratuita nacional disponível)",
        "cobertura_automatica": False,
        "link_consulta_manual_tjsp": gerar_link_consulta_manual_tjsp(),
        "observacao": (
            "Cole o CPF/CNPJ manualmente no link acima (captcha impede automação). "
            "Para cobertura nacional automatizada, considere um provedor pago com API "
            "(Escavador, Judit.io) e compare o custo por consulta com o Alude."
        ),
        "processos": [],
    }
