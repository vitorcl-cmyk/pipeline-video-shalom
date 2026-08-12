"""Análise de ficha (triagem de candidato a inquilino) por CPF/CNPJ.

Consolida num relatório único o que dá pra automatizar de graça e
legalmente (dados cadastrais de CNPJ, servidor público federal/sanções) com
o que precisa ser colado manualmente (SPC/Serasa pago, judicial via TJSP) —
alternativa interna ao Detetive Alude. Fica solta, sem vínculo obrigatório
com um Inquilino: a triagem acontece antes do candidato virar Inquilino
cadastrado no sistema.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import AnaliseFicha
from app.schemas import AnaliseFichaOut, NovaAnaliseRequest, ParecerRequest, SpcDataRequest
from app.services import cnpj_lookup, judicial_lookup, report, servidor_publico
from app.utils import DocumentoInvalido, identificar_documento

router = APIRouter(prefix="/ficha", tags=["ficha"], dependencies=[Depends(get_current_user)])


@router.post("", status_code=status.HTTP_201_CREATED)
def criar_analise(payload: NovaAnaliseRequest, db: Session = Depends(get_db)):
    """Cria uma análise a partir de um único campo CPF/CNPJ e já dispara
    automaticamente as consultas gratuitas disponíveis para aquele tipo de
    documento."""
    try:
        tipo, digitos = identificar_documento(payload.documento)
    except DocumentoInvalido as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    analise = AnaliseFicha(documento=digitos, tipo_documento=tipo, nome_candidato=payload.nome_candidato)
    db.add(analise)
    db.flush()

    avisos: list[str] = []

    if tipo == "cnpj":
        try:
            analise.dados_cadastrais = cnpj_lookup.consultar_cnpj(digitos)
        except cnpj_lookup.ConsultaIndisponivel as e:
            avisos.append(f"Dados cadastrais indisponíveis: {e}")

    # Situação judicial: sempre gera o registro (com link manual quando não há automação)
    analise.dados_judiciais = judicial_lookup.consultar_processos(digitos, tipo)

    # Servidor público / sanções: requer token; se não configurado, apenas avisa
    try:
        dados_servidor: dict = {}
        if tipo == "cpf":
            dados_servidor = servidor_publico.consultar_servidor_federal(digitos)
        dados_servidor["sancoes"] = servidor_publico.consultar_sancoes(digitos)
        analise.dados_servidor = dados_servidor
    except servidor_publico.TokenNaoConfigurado as e:
        avisos.append(str(e))
    except servidor_publico.ConsultaIndisponivel as e:
        avisos.append(f"Portal da Transparência indisponível: {e}")

    db.commit()
    return {"analise_id": analise.id, "tipo_documento": tipo, "avisos": avisos}


@router.get("", response_model=list[AnaliseFichaOut])
def listar(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(AnaliseFicha).order_by(AnaliseFicha.created_at.desc()).limit(limit).all()


@router.get("/{analise_id}", response_model=AnaliseFichaOut)
def obter_analise(analise_id: str, db: Session = Depends(get_db)):
    analise = db.get(AnaliseFicha, analise_id)
    if not analise:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Análise não encontrada")
    return analise


@router.post("/{analise_id}/spc", response_model=AnaliseFichaOut)
def registrar_spc(analise_id: str, payload: SpcDataRequest, db: Session = Depends(get_db)):
    """Cola aqui os dados da consulta SPC/Serasa paga que já é feita hoje."""
    analise = db.get(AnaliseFicha, analise_id)
    if not analise:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Análise não encontrada")
    dados = {k: v for k, v in payload.model_dump().items() if v is not None}
    analise.dados_spc = dados
    db.commit()
    db.refresh(analise)
    return analise


@router.post("/{analise_id}/parecer", response_model=AnaliseFichaOut)
def registrar_parecer(analise_id: str, payload: ParecerRequest, db: Session = Depends(get_db)):
    analise = db.get(AnaliseFicha, analise_id)
    if not analise:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Análise não encontrada")
    analise.parecer_final = payload.parecer
    analise.observacoes = payload.observacoes
    db.commit()
    db.refresh(analise)
    return analise


@router.get("/{analise_id}/relatorio", response_class=PlainTextResponse)
def relatorio(analise_id: str, db: Session = Depends(get_db)):
    analise = db.get(AnaliseFicha, analise_id)
    if not analise:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Análise não encontrada")
    return report.gerar_relatorio(analise)
