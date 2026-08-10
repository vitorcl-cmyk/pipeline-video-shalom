"""Pydantic schemas (request/response) para auth e cadastros essenciais."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import ContractStatus, PropertyStatus, PropertyType, ReadjustmentIndex

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: str | None
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None


# ---------------------------------------------------------------------------
# Owner (Proprietário)
# ---------------------------------------------------------------------------


class OwnerBase(BaseModel):
    nome: str
    cpf_cnpj: str | None = None
    email: str | None = None
    telefone: str | None = None
    endereco: str | None = None
    banco: str | None = None
    agencia: str | None = None
    conta: str | None = None
    chave_pix: str | None = None
    observacoes: str | None = None


class OwnerCreate(OwnerBase):
    pass


class OwnerUpdate(OwnerBase):
    nome: str | None = None


class OwnerOut(OwnerBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Tenant (Inquilino)
# ---------------------------------------------------------------------------


class TenantBase(BaseModel):
    nome: str
    cpf_cnpj: str | None = None
    email: str | None = None
    telefone: str | None = None
    endereco: str | None = None
    observacoes: str | None = None


class TenantCreate(TenantBase):
    pass


class TenantUpdate(TenantBase):
    nome: str | None = None


class TenantOut(TenantBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Property (Imóvel)
# ---------------------------------------------------------------------------


class PropertyBase(BaseModel):
    owner_id: str
    tipo: PropertyType = PropertyType.APARTAMENTO
    status: PropertyStatus = PropertyStatus.DISPONIVEL
    endereco: str
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    uf: str | None = None
    cep: str | None = None
    matricula: str | None = None
    valor_iptu_anual: float | None = None
    valor_condominio: float | None = None
    observacoes: str | None = None


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    owner_id: str | None = None
    tipo: PropertyType | None = None
    status: PropertyStatus | None = None
    endereco: str | None = None
    numero: str | None = None
    complemento: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    uf: str | None = None
    cep: str | None = None
    matricula: str | None = None
    valor_iptu_anual: float | None = None
    valor_condominio: float | None = None
    observacoes: str | None = None


class PropertyOut(PropertyBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    owner: OwnerOut | None = None


# ---------------------------------------------------------------------------
# Contract (Contrato)
# ---------------------------------------------------------------------------


class ContractBase(BaseModel):
    property_id: str
    tenant_id: str
    data_inicio: date
    data_fim: date | None = None
    dia_vencimento: int = 5
    valor_aluguel: float
    taxa_administracao_percentual: float = 10.0
    indice_reajuste: ReadjustmentIndex = ReadjustmentIndex.IGPM
    status: ContractStatus = ContractStatus.ATIVO
    fiador_nome: str | None = None
    fiador_cpf: str | None = None
    fiador_telefone: str | None = None
    observacoes: str | None = None


class ContractCreate(ContractBase):
    pass


class ContractUpdate(BaseModel):
    property_id: str | None = None
    tenant_id: str | None = None
    data_inicio: date | None = None
    data_fim: date | None = None
    dia_vencimento: int | None = None
    valor_aluguel: float | None = None
    taxa_administracao_percentual: float | None = None
    indice_reajuste: ReadjustmentIndex | None = None
    status: ContractStatus | None = None
    fiador_nome: str | None = None
    fiador_cpf: str | None = None
    fiador_telefone: str | None = None
    observacoes: str | None = None


class ContractOut(ContractBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    property: PropertyOut | None = None
    tenant: TenantOut | None = None


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class DashboardSummary(BaseModel):
    total_proprietarios: int
    total_inquilinos: int
    total_imoveis: int
    imoveis_disponiveis: int
    imoveis_alugados: int
    contratos_ativos: int
    contratos_vencendo_30_dias: int
    receita_aluguel_mensal: float
    receita_administracao_mensal: float
