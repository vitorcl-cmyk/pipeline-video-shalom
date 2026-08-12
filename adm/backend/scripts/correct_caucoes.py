"""Roda uma vez por mês (systemd timer no servidor) e corrige
automaticamente o valor de todos os depósitos caução ativos, buscando a
taxa da poupança na API pública do Banco Central. Não depende de ninguém
digitar nada: se a API do BCB estiver fora do ar num mês, o contrato fica
pendente e é corrigido no mês seguinte (a correção busca o acumulado desde
a última correção aplicada, não só o último mês).

Uso: dentro de adm/backend, com o venv ativo:
  python -m scripts.correct_caucoes
"""
import logging

from app.caucao_service import CaucaoCorrectionError, apply_correction
from app.database import SessionLocal
from app.models import Contract, ContractStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("correct_caucoes")


def main() -> None:
    db = SessionLocal()
    try:
        contracts = (
            db.query(Contract)
            .filter(
                Contract.status == ContractStatus.ATIVO,
                Contract.valor_caucao.isnot(None),
                Contract.data_deposito_caucao.isnot(None),
            )
            .all()
        )
        logger.info("Verificando %d contrato(s) com depósito caução ativo", len(contracts))
        for contract in contracts:
            try:
                log = apply_correction(db, contract)
                db.commit()
                logger.info(
                    "Contrato %s: caução corrigida de R$ %.2f para R$ %.2f (%s, competência %s)",
                    contract.id,
                    float(log.valor_anterior),
                    float(log.valor_novo),
                    log.fonte,
                    log.competencia,
                )
            except CaucaoCorrectionError as exc:
                db.rollback()
                logger.warning("Contrato %s: não corrigido (%s)", contract.id, exc)
    finally:
        db.close()


if __name__ == "__main__":
    main()
