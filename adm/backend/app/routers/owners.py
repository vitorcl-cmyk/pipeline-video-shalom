"""CRUD de Proprietários."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Owner, User
from app.schemas import OwnerCreate, OwnerOut, OwnerUpdate

router = APIRouter(prefix="/owners", tags=["owners"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[OwnerOut])
def list_owners(q: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Owner)
    if q:
        like = f"%{q}%"
        query = query.filter((Owner.nome.ilike(like)) | (Owner.cpf_cnpj.ilike(like)))
    return query.order_by(Owner.nome).all()


@router.post("", response_model=OwnerOut, status_code=status.HTTP_201_CREATED)
def create_owner(payload: OwnerCreate, db: Session = Depends(get_db)):
    if payload.cpf_cnpj:
        existing = db.query(Owner).filter(Owner.cpf_cnpj == payload.cpf_cnpj).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="CPF/CNPJ já cadastrado")

    owner = Owner(**payload.model_dump())
    db.add(owner)
    db.commit()
    db.refresh(owner)
    return owner


@router.get("/{owner_id}", response_model=OwnerOut)
def get_owner(owner_id: str, db: Session = Depends(get_db)):
    owner = db.get(Owner, owner_id)
    if not owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proprietário não encontrado")
    return owner


@router.put("/{owner_id}", response_model=OwnerOut)
def update_owner(owner_id: str, payload: OwnerUpdate, db: Session = Depends(get_db)):
    owner = db.get(Owner, owner_id)
    if not owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proprietário não encontrado")

    data = payload.model_dump(exclude_unset=True)
    if "cpf_cnpj" in data and data["cpf_cnpj"] and data["cpf_cnpj"] != owner.cpf_cnpj:
        existing = db.query(Owner).filter(Owner.cpf_cnpj == data["cpf_cnpj"]).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="CPF/CNPJ já cadastrado")

    for field, value in data.items():
        setattr(owner, field, value)

    db.commit()
    db.refresh(owner)
    return owner


@router.delete("/{owner_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_owner(owner_id: str, db: Session = Depends(get_db)):
    owner = db.get(Owner, owner_id)
    if not owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proprietário não encontrado")
    if owner.properties:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não é possível excluir: proprietário possui imóveis cadastrados",
        )
    db.delete(owner)
    db.commit()
