"""CRUD de Contratos de locação.

Regra de negócio simples: ao criar/ativar um contrato, o imóvel passa para
"alugado"; ao encerrar o contrato, o imóvel volta para "disponivel" (caso
não haja outro contrato ativo apontando para ele).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from datetime import date as date_cls

from app.auth import get_current_user
from app.database import get_db
from app.models import Contract, ContractStatus, Property, PropertyStatus, ReadjustmentLog, Tenant, User
from app.schemas import ContractCreate, ContractOut, ContractUpdate, ReadjustmentApply, ReadjustmentLogOut
from app.utils import next_due_date

router = APIRouter(prefix="/contracts", tags=["contracts"], dependencies=[Depends(get_current_user)])


def _base_query(db: Session):
    return db.query(Contract).options(
        joinedload(Contract.property).joinedload(Property.owner),
        joinedload(Contract.tenant),
    )


def _sync_property_status(db: Session, prop: Property) -> None:
    has_active = (
        db.query(Contract)
        .filter(Contract.property_id == prop.id, Contract.status == ContractStatus.ATIVO)
        .first()
    )
    prop.status = PropertyStatus.ALUGADO if has_active else PropertyStatus.DISPONIVEL


@router.get("", response_model=list[ContractOut])
def list_contracts(
    status_filter: ContractStatus | None = None,
    property_id: str | None = None,
    tenant_id: str | None = None,
    db: Session = Depends(get_db),
):
    query = _base_query(db)
    if status_filter:
        query = query.filter(Contract.status == status_filter)
    if property_id:
        query = query.filter(Contract.property_id == property_id)
    if tenant_id:
        query = query.filter(Contract.tenant_id == tenant_id)
    contracts = query.all()

    # Contratos ativos primeiro, ordenados por quem vence o boleto mais
    # cedo — é o que precisa de atenção primeiro. O resto (encerrado/
    # inadimplente) vem depois, mais recente primeiro.
    ativos = sorted(
        (c for c in contracts if c.status == ContractStatus.ATIVO),
        key=lambda c: next_due_date(c.dia_vencimento),
    )
    outros = sorted(
        (c for c in contracts if c.status != ContractStatus.ATIVO),
        key=lambda c: c.data_inicio,
        reverse=True,
    )
    return ativos + outros


@router.post("", response_model=ContractOut, status_code=status.HTTP_201_CREATED)
def create_contract(payload: ContractCreate, db: Session = Depends(get_db)):
    prop = db.get(Property, payload.property_id)
    if not prop:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Imóvel não encontrado")
    tenant = db.get(Tenant, payload.tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inquilino não encontrado")

    contract = Contract(**payload.model_dump())
    db.add(contract)
    db.flush()  # garante que o INSERT seja visível para a query de sincronização abaixo
    _sync_property_status(db, prop)
    db.commit()
    db.refresh(contract)
    return contract


@router.get("/{contract_id}", response_model=ContractOut)
def get_contract(contract_id: str, db: Session = Depends(get_db)):
    contract = _base_query(db).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")
    return contract


@router.put("/{contract_id}", response_model=ContractOut)
def update_contract(contract_id: str, payload: ContractUpdate, db: Session = Depends(get_db)):
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")

    data = payload.model_dump(exclude_unset=True)

    new_property_id = data.get("property_id", contract.property_id)
    if "property_id" in data:
        prop = db.get(Property, data["property_id"])
        if not prop:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Imóvel não encontrado")
    if "tenant_id" in data:
        tenant = db.get(Tenant, data["tenant_id"])
        if not tenant:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inquilino não encontrado")

    old_property_id = contract.property_id
    for field, value in data.items():
        setattr(contract, field, value)
    db.flush()  # garante que a mudança seja visível para a query de sincronização abaixo

    affected_property_ids = {old_property_id, new_property_id}
    for pid in affected_property_ids:
        prop = db.get(Property, pid)
        if prop:
            _sync_property_status(db, prop)

    db.commit()
    db.refresh(contract)
    return contract


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contract(contract_id: str, db: Session = Depends(get_db)):
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")

    prop = db.get(Property, contract.property_id)
    db.delete(contract)
    db.flush()
    if prop:
        _sync_property_status(db, prop)
    db.commit()


@router.get("/{contract_id}/readjustments", response_model=list[ReadjustmentLogOut])
def list_readjustments(contract_id: str, db: Session = Depends(get_db)):
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")
    return (
        db.query(ReadjustmentLog)
        .filter(ReadjustmentLog.contract_id == contract_id)
        .order_by(ReadjustmentLog.data.desc())
        .all()
    )


@router.post("/{contract_id}/readjustments", response_model=ContractOut, status_code=status.HTTP_201_CREATED)
def apply_readjustment(contract_id: str, payload: ReadjustmentApply, db: Session = Depends(get_db)):
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")

    data_reajuste = payload.data or date_cls.today()
    valor_anterior = float(contract.valor_aluguel)
    valor_novo = round(valor_anterior * (1 + payload.percentual / 100), 2)

    log = ReadjustmentLog(
        contract_id=contract_id,
        data=data_reajuste,
        indice=contract.indice_reajuste,
        percentual=payload.percentual,
        valor_anterior=valor_anterior,
        valor_novo=valor_novo,
        observacoes=payload.observacoes,
    )
    db.add(log)

    contract.valor_aluguel = valor_novo
    contract.data_ultimo_reajuste = data_reajuste

    db.commit()
    db.refresh(contract)
    return _base_query(db).filter(Contract.id == contract_id).first()
