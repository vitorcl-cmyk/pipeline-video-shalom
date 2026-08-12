"""Pydantic schemas (request/response) para auth e cadastros essenciais."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, computed_field

from app.models import (
    ChargeKind,
    ChargeLaunchStatus,
    ContractStatus,
    PropertyStatus,
    PropertyType,
    ReadjustmentIndex,
)
from app.utils import next_caucao_correction_date, next_due_date, next_readjustment_date

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


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    is_active: bool | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


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
    data_ultimo_reajuste: date | None = None
    valor_caucao: float | None = None
    data_deposito_caucao: date | None = None
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
    data_ultimo_reajuste: date | None = None
    valor_caucao: float | None = None
    data_deposito_caucao: date | None = None
    status: ContractStatus | None = None
    fiador_nome: str | None = None
    fiador_cpf: str | None = None
    fiador_telefone: str | None = None
    observacoes: str | None = None


class ContractOut(ContractBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime

    # Precisa vir ANTES do campo "property" abaixo: um campo do modelo
    # chamado "property" reatribui esse nome dentro do corpo da classe,
    # o que quebraria o decorator embutido @property se ele viesse depois.
    @computed_field
    @property
    def proxima_data_reajuste(self) -> date | None:
        if self.indice_reajuste == ReadjustmentIndex.NENHUM:
            return None
        return next_readjustment_date(self.data_inicio, self.data_ultimo_reajuste)

    @computed_field
    @property
    def proximo_vencimento(self) -> date:
        return next_due_date(self.dia_vencimento)

    @computed_field
    @property
    def proxima_correcao_caucao(self) -> date | None:
        if not self.valor_caucao or not self.data_deposito_caucao:
            return None
        return next_caucao_correction_date(self.data_deposito_caucao, self.data_ultima_correcao_caucao)

    data_ultima_correcao_caucao: date | None = None
    property: PropertyOut | None = None
    tenant: TenantOut | None = None


class ReadjustmentApply(BaseModel):
    percentual: float
    data: date | None = None
    observacoes: str | None = None


class ReadjustmentLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contract_id: str
    data: date
    indice: ReadjustmentIndex
    percentual: float
    valor_anterior: float
    valor_novo: float
    observacoes: str | None
    created_at: datetime


class CaucaoCorrectionApply(BaseModel):
    competencia: str | None = None  # "AAAA-MM"; default = mês atual
    # Se omitido, tenta buscar a taxa da poupança automaticamente na API do BCB.
    taxa_percentual: float | None = None


class CaucaoCorrectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contract_id: str
    competencia: str
    taxa_percentual: float
    valor_anterior: float
    valor_novo: float
    fonte: str
    automatica: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Charge (conta fixa/variável) e ChargeLaunch (lançamento mensal)
# ---------------------------------------------------------------------------


class ChargeBase(BaseModel):
    nome: str
    tipo: ChargeKind = ChargeKind.VARIAVEL
    valor_fixo: float | None = None
    dia_vencimento: int | None = None
    meses_pausados: list[int] = []  # 1-12, meses em que essa conta não é cobrada
    ativa: bool = True
    observacoes: str | None = None


class ChargeCreate(ChargeBase):
    pass


class ChargeUpdate(BaseModel):
    nome: str | None = None
    tipo: ChargeKind | None = None
    valor_fixo: float | None = None
    dia_vencimento: int | None = None
    meses_pausados: list[int] | None = None
    ativa: bool | None = None
    observacoes: str | None = None


class ChargeOut(ChargeBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contract_id: str
    created_at: datetime


class ChargeLaunchBase(BaseModel):
    competencia: str  # "AAAA-MM"
    valor: float
    vencimento: date | None = None
    status: ChargeLaunchStatus = ChargeLaunchStatus.PENDENTE
    pago_em: date | None = None
    observacoes: str | None = None


class ChargeLaunchCreate(ChargeLaunchBase):
    valor: float | None = None  # se omitido numa conta fixa, usa charge.valor_fixo


class ChargeLaunchUpdate(BaseModel):
    valor: float | None = None
    vencimento: date | None = None
    status: ChargeLaunchStatus | None = None
    pago_em: date | None = None
    observacoes: str | None = None


class ChargeLaunchOut(ChargeLaunchBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    charge_id: str
    created_at: datetime


class ChargeWithLaunchesOut(ChargeOut):
    launches: list[ChargeLaunchOut] = []


# ---------------------------------------------------------------------------
# Billing (emissão de cobrança mensal: aluguel + contas fixas/variáveis)
# ---------------------------------------------------------------------------


class BillingItemPreview(BaseModel):
    charge_id: str
    nome: str
    tipo: ChargeKind
    valor: float | None  # None quando é variável e ainda não foi lançado neste mês
    needs_input: bool  # True = precisa que o usuário informe o valor antes de emitir


class BillingPreviewOut(BaseModel):
    contract_id: str
    competencia: str
    valor_aluguel: float
    itens: list[BillingItemPreview]
    ja_emitida: bool  # já existe uma cobrança gerada para esta competência


class BillingGenerateRequest(BaseModel):
    competencia: str
    vencimento: date | None = None
    valores: dict[str, float] = {}  # charge_id -> valor (obrigatório para variáveis sem lançamento)


class InvoiceItemOut(BaseModel):
    nome: str
    tipo: str
    valor: float


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    contract_id: str
    competencia: str
    valor_aluguel: float
    valor_contas: float
    valor_total: float
    valor_repasse: float
    itens: list[InvoiceItemOut]
    vencimento: date | None
    status: ChargeLaunchStatus
    pago_em: date | None
    created_at: datetime


class InvoiceUpdate(BaseModel):
    status: ChargeLaunchStatus | None = None
    vencimento: date | None = None
    pago_em: date | None = None


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
    contas_variaveis_pendentes: int
    contratos_reajuste_proximo: int
