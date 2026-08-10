"""CRUD de Inquilinos."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Tenant, User
from app.schemas import TenantCreate, TenantOut, TenantUpdate

router = APIRouter(prefix="/tenants", tags=["tenants"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[TenantOut])
def list_tenants(q: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Tenant)
    if q:
        like = f"%{q}%"
        query = query.filter((Tenant.nome.ilike(like)) | (Tenant.cpf_cnpj.ilike(like)))
    return query.order_by(Tenant.nome).all()


@router.post("", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
def create_tenant(payload: TenantCreate, db: Session = Depends(get_db)):
    if payload.cpf_cnpj:
        existing = db.query(Tenant).filter(Tenant.cpf_cnpj == payload.cpf_cnpj).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="CPF/CNPJ já cadastrado")

    tenant = Tenant(**payload.model_dump())
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@router.get("/{tenant_id}", response_model=TenantOut)
def get_tenant(tenant_id: str, db: Session = Depends(get_db)):
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inquilino não encontrado")
    return tenant


@router.put("/{tenant_id}", response_model=TenantOut)
def update_tenant(tenant_id: str, payload: TenantUpdate, db: Session = Depends(get_db)):
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inquilino não encontrado")

    data = payload.model_dump(exclude_unset=True)
    if "cpf_cnpj" in data and data["cpf_cnpj"] and data["cpf_cnpj"] != tenant.cpf_cnpj:
        existing = db.query(Tenant).filter(Tenant.cpf_cnpj == data["cpf_cnpj"]).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="CPF/CNPJ já cadastrado")

    for field, value in data.items():
        setattr(tenant, field, value)

    db.commit()
    db.refresh(tenant)
    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(tenant_id: str, db: Session = Depends(get_db)):
    tenant = db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inquilino não encontrado")
    if tenant.contracts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não é possível excluir: inquilino possui contratos cadastrados",
        )
    db.delete(tenant)
    db.commit()
