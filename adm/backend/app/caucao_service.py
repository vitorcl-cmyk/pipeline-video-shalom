"""Lógica de correção monetária do depósito caução — compartilhada entre o
endpoint da API (correção manual/avulsa pelo painel) e o script de execução
mensal automática (scripts/correct_caucoes.py, rodado por systemd timer no
servidor de produção)."""
from datetime import date

from sqlalchemy.orm import Session

from app.bcb import SGS_POUPANCA_SERIE, BcbUnavailableError, compound_correction, fetch_poupanca_rates
from app.models import CaucaoCorrection, Contract


class CaucaoCorrectionError(Exception):
    pass


def apply_correction(
    db: Session,
    contract: Contract,
    *,
    competencia: str | None = None,
    taxa_percentual: float | None = None,
) -> CaucaoCorrection:
    """Cria um lançamento de correção pra este contrato e atualiza
    contract.valor_caucao. Não faz commit — quem chama decide quando
    commitar (permite aplicar em lote e reverter tudo se algo falhar).

    Se taxa_percentual for omitido, busca a taxa da poupança automaticamente
    na API do Banco Central para todo o período desde a última correção
    (ou desde o depósito, se nunca foi corrigido)."""
    if not contract.valor_caucao or not contract.data_deposito_caucao:
        raise CaucaoCorrectionError("Contrato não tem valor de caução cadastrado")

    competencia = competencia or date.today().strftime("%Y-%m")
    already = (
        db.query(CaucaoCorrection)
        .filter(CaucaoCorrection.contract_id == contract.id, CaucaoCorrection.competencia == competencia)
        .first()
    )
    if already:
        raise CaucaoCorrectionError(f"já existe correção lançada para {competencia}")

    automatica = taxa_percentual is None
    valor_anterior = float(contract.valor_caucao)

    if automatica:
        base = contract.data_ultima_correcao_caucao or contract.data_deposito_caucao
        try:
            rates = fetch_poupanca_rates(base, date.today())
        except BcbUnavailableError as exc:
            raise CaucaoCorrectionError(
                f"não foi possível buscar a taxa da poupança automaticamente ({exc}) — "
                "informe o percentual manualmente"
            ) from exc
        if not rates:
            raise CaucaoCorrectionError(
                "nenhuma taxa de poupança encontrada no período — informe o percentual manualmente"
            )
        valor_novo = compound_correction(valor_anterior, [r["taxa_percentual"] for r in rates])
        taxa_final = round(((valor_novo / valor_anterior) - 1) * 100, 5) if valor_anterior else 0.0
        fonte = f"Poupança (BCB SGS série {SGS_POUPANCA_SERIE}) — {len(rates)} competência(s)"
    else:
        valor_novo = round(valor_anterior * (1 + taxa_percentual / 100), 2)
        taxa_final = taxa_percentual
        fonte = "Informado manualmente"

    log = CaucaoCorrection(
        contract_id=contract.id,
        competencia=competencia,
        taxa_percentual=taxa_final,
        valor_anterior=valor_anterior,
        valor_novo=valor_novo,
        fonte=fonte,
        automatica=automatica,
    )
    db.add(log)
    contract.valor_caucao = valor_novo
    contract.data_ultima_correcao_caucao = date.today()
    return log
