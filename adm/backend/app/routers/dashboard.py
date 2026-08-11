"""Resumo/indicadores para a tela inicial do painel."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    ChargeLaunch,
    ChargeLaunchStatus,
    Contract,
    ContractStatus,
    Owner,
    Property,
    PropertyStatus,
    Tenant,
)
from app.schemas import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_user)])


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db)):
    total_proprietarios = db.query(func.count(Owner.id)).scalar() or 0
    total_inquilinos = db.query(func.count(Tenant.id)).scalar() or 0
    total_imoveis = db.query(func.count(Property.id)).scalar() or 0
    imoveis_disponiveis = (
        db.query(func.count(Property.id)).filter(Property.status == PropertyStatus.DISPONIVEL).scalar() or 0
    )
    imoveis_alugados = (
        db.query(func.count(Property.id)).filter(Property.status == PropertyStatus.ALUGADO).scalar() or 0
    )

    contratos_ativos_query = db.query(Contract).filter(Contract.status == ContractStatus.ATIVO)
    contratos_ativos = contratos_ativos_query.count()

    limite = date.today() + timedelta(days=30)
    contratos_vencendo = contratos_ativos_query.filter(
        Contract.data_fim.isnot(None), Contract.data_fim <= limite
    ).count()

    receita_aluguel = sum(float(c.valor_aluguel) for c in contratos_ativos_query.all())
    receita_administracao = sum(
        float(c.valor_aluguel) * float(c.taxa_administracao_percentual) / 100
        for c in contratos_ativos_query.all()
    )

    contas_variaveis_pendentes = (
        db.query(func.count(ChargeLaunch.id))
        .filter(ChargeLaunch.status != ChargeLaunchStatus.PAGA)
        .scalar()
        or 0
    )

    return DashboardSummary(
        total_proprietarios=total_proprietarios,
        total_inquilinos=total_inquilinos,
        total_imoveis=total_imoveis,
        imoveis_disponiveis=imoveis_disponiveis,
        imoveis_alugados=imoveis_alugados,
        contratos_ativos=contratos_ativos,
        contratos_vencendo_30_dias=contratos_vencendo,
        receita_aluguel_mensal=round(receita_aluguel, 2),
        receita_administracao_mensal=round(receita_administracao, 2),
        contas_variaveis_pendentes=contas_variaveis_pendentes,
    )
