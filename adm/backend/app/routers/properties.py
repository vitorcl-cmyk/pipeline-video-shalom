"""CRUD de Imóveis."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.models import Owner, Property, PropertyStatus, User
from app.schemas import PropertyCreate, PropertyOut, PropertyUpdate

router = APIRouter(prefix="/properties", tags=["properties"], dependencies=[Depends(get_current_user)])


def _base_query(db: Session):
    return db.query(Property).options(joinedload(Property.owner))


@router.get("", response_model=list[PropertyOut])
def list_properties(
    owner_id: str | None = None,
    status_filter: PropertyStatus | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
):
    query = _base_query(db)
    if owner_id:
        query = query.filter(Property.owner_id == owner_id)
    if status_filter:
        query = query.filter(Property.status == status_filter)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Property.endereco.ilike(like))
            | (Property.bairro.ilike(like))
            | (Property.cidade.ilike(like))
        )
    return query.order_by(Property.endereco).all()


@router.post("", response_model=PropertyOut, status_code=status.HTTP_201_CREATED)
def create_property(payload: PropertyCreate, db: Session = Depends(get_db)):
    owner = db.get(Owner, payload.owner_id)
    if not owner:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Proprietário não encontrado")

    prop = Property(**payload.model_dump())
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


@router.get("/{property_id}", response_model=PropertyOut)
def get_property(property_id: str, db: Session = Depends(get_db)):
    prop = _base_query(db).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imóvel não encontrado")
    return prop


@router.put("/{property_id}", response_model=PropertyOut)
def update_property(property_id: str, payload: PropertyUpdate, db: Session = Depends(get_db)):
    prop = db.get(Property, property_id)
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imóvel não encontrado")

    data = payload.model_dump(exclude_unset=True)
    if "owner_id" in data and data["owner_id"]:
        owner = db.get(Owner, data["owner_id"])
        if not owner:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Proprietário não encontrado")

    for field, value in data.items():
        setattr(prop, field, value)

    db.commit()
    db.refresh(prop)
    return prop


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property(property_id: str, db: Session = Depends(get_db)):
    prop = db.get(Property, property_id)
    if not prop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imóvel não encontrado")
    if prop.contracts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Não é possível excluir: imóvel possui contratos cadastrados",
        )
    db.delete(prop)
    db.commit()
