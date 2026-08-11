"""Contas fixas/variáveis por contrato e seus lançamentos mensais.

Contas fixas (aluguel, tx. administração) têm o mesmo valor todo mês —
`valor_fixo` na própria Charge. Contas variáveis (água, condomínio, IPTU
quando rateado, luz de área comum etc.) mudam de valor mês a mês porque
dependem do rateio feito pelo síndico/concessionária, então cada mês exige
um lançamento (ChargeLaunch) com o valor daquela competência.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models import Charge, ChargeKind, ChargeLaunch, Contract, User
from app.schemas import (
    ChargeCreate,
    ChargeLaunchCreate,
    ChargeLaunchOut,
    ChargeLaunchUpdate,
    ChargeOut,
    ChargeUpdate,
    ChargeWithLaunchesOut,
)

router = APIRouter(tags=["charges"], dependencies=[Depends(get_current_user)])


# ---------------------------------------------------------------------------
# Charges (definições, aninhadas em /contracts/{contract_id}/charges)
# ---------------------------------------------------------------------------


@router.get("/contracts/{contract_id}/charges", response_model=list[ChargeWithLaunchesOut])
def list_contract_charges(contract_id: str, db: Session = Depends(get_db)):
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")
    return (
        db.query(Charge)
        .options(joinedload(Charge.launches))
        .filter(Charge.contract_id == contract_id)
        .order_by(Charge.nome)
        .all()
    )


@router.post("/contracts/{contract_id}/charges", response_model=ChargeOut, status_code=status.HTTP_201_CREATED)
def create_contract_charge(contract_id: str, payload: ChargeCreate, db: Session = Depends(get_db)):
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")
    if payload.tipo == ChargeKind.FIXA and payload.valor_fixo is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Conta fixa precisa de valor_fixo")

    charge = Charge(contract_id=contract_id, **payload.model_dump())
    db.add(charge)
    db.commit()
    db.refresh(charge)
    return charge


@router.put("/charges/{charge_id}", response_model=ChargeOut)
def update_charge(charge_id: str, payload: ChargeUpdate, db: Session = Depends(get_db)):
    charge = db.get(Charge, charge_id)
    if not charge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta não encontrada")

    data = payload.model_dump(exclude_unset=True)
    new_tipo = data.get("tipo", charge.tipo)
    new_valor_fixo = data.get("valor_fixo", charge.valor_fixo)
    if new_tipo == ChargeKind.FIXA and new_valor_fixo is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Conta fixa precisa de valor_fixo")

    for field, value in data.items():
        setattr(charge, field, value)
    db.commit()
    db.refresh(charge)
    return charge


@router.delete("/charges/{charge_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_charge(charge_id: str, db: Session = Depends(get_db)):
    charge = db.get(Charge, charge_id)
    if not charge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta não encontrada")
    db.delete(charge)
    db.commit()


# ---------------------------------------------------------------------------
# Lançamentos mensais (/charges/{charge_id}/launches)
# ---------------------------------------------------------------------------


@router.get("/charges/{charge_id}/launches", response_model=list[ChargeLaunchOut])
def list_charge_launches(charge_id: str, db: Session = Depends(get_db)):
    charge = db.get(Charge, charge_id)
    if not charge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta não encontrada")
    return (
        db.query(ChargeLaunch)
        .filter(ChargeLaunch.charge_id == charge_id)
        .order_by(ChargeLaunch.competencia.desc())
        .all()
    )


@router.post("/charges/{charge_id}/launches", response_model=ChargeLaunchOut, status_code=status.HTTP_201_CREATED)
def create_charge_launch(charge_id: str, payload: ChargeLaunchCreate, db: Session = Depends(get_db)):
    charge = db.get(Charge, charge_id)
    if not charge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conta não encontrada")

    valor = payload.valor
    if valor is None:
        if charge.tipo != ChargeKind.FIXA or charge.valor_fixo is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Informe o valor deste mês (obrigatório para contas variáveis, ex.: água)",
            )
        valor = charge.valor_fixo

    existing = (
        db.query(ChargeLaunch)
        .filter(ChargeLaunch.charge_id == charge_id, ChargeLaunch.competencia == payload.competencia)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe lançamento para a competência {payload.competencia}",
        )

    launch = ChargeLaunch(
        charge_id=charge_id,
        competencia=payload.competencia,
        valor=valor,
        vencimento=payload.vencimento,
        status=payload.status,
        pago_em=payload.pago_em,
        observacoes=payload.observacoes,
    )
    db.add(launch)
    db.commit()
    db.refresh(launch)
    return launch


@router.put("/charge-launches/{launch_id}", response_model=ChargeLaunchOut)
def update_charge_launch(launch_id: str, payload: ChargeLaunchUpdate, db: Session = Depends(get_db)):
    launch = db.get(ChargeLaunch, launch_id)
    if not launch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lançamento não encontrado")

    data = payload.model_dump(exclude_unset=True)
    if data.get("status") == "paga" and not data.get("pago_em") and not launch.pago_em:
        data["pago_em"] = date.today()

    for field, value in data.items():
        setattr(launch, field, value)
    db.commit()
    db.refresh(launch)
    return launch


@router.delete("/charge-launches/{launch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_charge_launch(launch_id: str, db: Session = Depends(get_db)):
    launch = db.get(ChargeLaunch, launch_id)
    if not launch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lançamento não encontrado")
    db.delete(launch)
    db.commit()
