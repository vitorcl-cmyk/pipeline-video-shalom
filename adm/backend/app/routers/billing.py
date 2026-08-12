"""Emissão da cobrança mensal de um contrato: junta aluguel + todas as
contas (fixas e variáveis) da competência num total só. Contas variáveis
sem lançamento ainda (ex.: água deste mês) aparecem no preview pedindo o
valor — só depois de informado é que dá pra emitir a cobrança."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Charge, ChargeKind, ChargeLaunch, Contract, Invoice, User
from app.schemas import (
    BillingGenerateRequest,
    BillingItemPreview,
    BillingPreviewOut,
    InvoiceOut,
    InvoiceUpdate,
)

router = APIRouter(tags=["billing"], dependencies=[Depends(get_current_user)])


def _active_charges(db: Session, contract_id: str) -> list[Charge]:
    return db.query(Charge).filter(Charge.contract_id == contract_id, Charge.ativa.is_(True)).order_by(Charge.nome).all()


def _is_paused(charge: Charge, competencia: str) -> bool:
    """Ex.: IPTU parcelado que não cobra em dezembro/janeiro em São Paulo —
    marcado em charge.meses_pausados (1-12)."""
    mes = int(competencia.split("-")[1])
    return mes in (charge.meses_pausados or [])


@router.get("/contracts/{contract_id}/billing/preview", response_model=BillingPreviewOut)
def preview_billing(contract_id: str, competencia: str, db: Session = Depends(get_db)):
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")

    itens: list[BillingItemPreview] = []
    for charge in _active_charges(db, contract_id):
        launch = (
            db.query(ChargeLaunch)
            .filter(ChargeLaunch.charge_id == charge.id, ChargeLaunch.competencia == competencia)
            .first()
        )
        if not launch and _is_paused(charge, competencia):
            continue  # ex.: IPTU não cobra este mês — nem aparece pedindo valor
        if launch:
            itens.append(BillingItemPreview(charge_id=charge.id, nome=charge.nome, tipo=charge.tipo, valor=float(launch.valor), needs_input=False))
        elif charge.tipo == ChargeKind.FIXA and charge.valor_fixo is not None:
            itens.append(BillingItemPreview(charge_id=charge.id, nome=charge.nome, tipo=charge.tipo, valor=float(charge.valor_fixo), needs_input=False))
        else:
            itens.append(BillingItemPreview(charge_id=charge.id, nome=charge.nome, tipo=charge.tipo, valor=None, needs_input=True))

    existing = db.query(Invoice).filter(Invoice.contract_id == contract_id, Invoice.competencia == competencia).first()

    return BillingPreviewOut(
        contract_id=contract_id,
        competencia=competencia,
        valor_aluguel=float(contract.valor_aluguel),
        itens=itens,
        ja_emitida=existing is not None,
    )


@router.post("/contracts/{contract_id}/billing", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def generate_billing(contract_id: str, payload: BillingGenerateRequest, db: Session = Depends(get_db)):
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")

    itens: list[dict] = []
    valor_contas = 0.0
    faltando: list[str] = []

    for charge in _active_charges(db, contract_id):
        launch = (
            db.query(ChargeLaunch)
            .filter(ChargeLaunch.charge_id == charge.id, ChargeLaunch.competencia == payload.competencia)
            .first()
        )
        if not launch and _is_paused(charge, payload.competencia):
            continue  # ex.: IPTU não cobra este mês — não entra na cobrança
        if not launch:
            valor = payload.valores.get(charge.id)
            if valor is None and charge.tipo == ChargeKind.FIXA:
                valor = charge.valor_fixo
            if valor is None:
                faltando.append(charge.nome)
                continue
            launch = ChargeLaunch(
                charge_id=charge.id,
                competencia=payload.competencia,
                valor=valor,
                vencimento=payload.vencimento,
            )
            db.add(launch)

        itens.append({"nome": charge.nome, "tipo": charge.tipo.value, "valor": float(launch.valor)})
        valor_contas += float(launch.valor)

    if faltando:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Informe o valor deste mês para: {', '.join(faltando)}",
        )

    valor_aluguel = float(contract.valor_aluguel)
    valor_total = valor_aluguel + valor_contas
    valor_repasse = round(valor_aluguel * (1 - float(contract.taxa_administracao_percentual) / 100), 2)

    invoice = db.query(Invoice).filter(Invoice.contract_id == contract_id, Invoice.competencia == payload.competencia).first()
    if invoice:
        invoice.valor_aluguel = valor_aluguel
        invoice.valor_contas = valor_contas
        invoice.valor_total = valor_total
        invoice.valor_repasse = valor_repasse
        invoice.itens = itens
        if payload.vencimento:
            invoice.vencimento = payload.vencimento
    else:
        invoice = Invoice(
            contract_id=contract_id,
            competencia=payload.competencia,
            valor_aluguel=valor_aluguel,
            valor_contas=valor_contas,
            valor_total=valor_total,
            valor_repasse=valor_repasse,
            itens=itens,
            vencimento=payload.vencimento,
        )
        db.add(invoice)

    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/contracts/{contract_id}/billing", response_model=list[InvoiceOut])
def list_invoices(contract_id: str, db: Session = Depends(get_db)):
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contrato não encontrado")
    return (
        db.query(Invoice)
        .filter(Invoice.contract_id == contract_id)
        .order_by(Invoice.competencia.desc())
        .all()
    )


@router.put("/invoices/{invoice_id}", response_model=InvoiceOut)
def update_invoice(invoice_id: str, payload: InvoiceUpdate, db: Session = Depends(get_db)):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cobrança não encontrada")

    data = payload.model_dump(exclude_unset=True)
    if data.get("status") == "paga" and not data.get("pago_em") and not invoice.pago_em:
        data["pago_em"] = date.today()

    for field, value in data.items():
        setattr(invoice, field, value)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(invoice_id: str, db: Session = Depends(get_db)):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cobrança não encontrada")
    db.delete(invoice)
    db.commit()
