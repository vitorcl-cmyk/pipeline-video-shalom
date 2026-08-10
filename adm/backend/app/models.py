"""SQLAlchemy ORM models: cadastros essenciais de administração de locação.

Domínio: Proprietário (dono do imóvel), Inquilino (locatário), Imóvel
(pertence a um proprietário) e Contrato (liga um imóvel a um inquilino).
"""
import enum
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PropertyType(str, enum.Enum):
    APARTAMENTO = "apartamento"
    CASA = "casa"
    COMERCIAL = "comercial"
    TERRENO = "terreno"
    OUTRO = "outro"


class PropertyStatus(str, enum.Enum):
    DISPONIVEL = "disponivel"
    ALUGADO = "alugado"
    MANUTENCAO = "manutencao"
    INATIVO = "inativo"


class ContractStatus(str, enum.Enum):
    ATIVO = "ativo"
    ENCERRADO = "encerrado"
    INADIMPLENTE = "inadimplente"


class ReadjustmentIndex(str, enum.Enum):
    IGPM = "igpm"
    IPCA = "ipca"
    NENHUM = "nenhum"


class User(Base):
    """Usuário da equipe Shalom com acesso ao painel administrativo."""

    __tablename__ = "adm_users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Owner(Base):
    """Proprietário: dono de um ou mais imóveis administrados pela Shalom."""

    __tablename__ = "owners"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    nome: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cpf_cnpj: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    endereco: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Dados bancários para repasse (usados no futuro módulo financeiro)
    banco: Mapped[str | None] = mapped_column(String(100), nullable=True)
    agencia: Mapped[str | None] = mapped_column(String(20), nullable=True)
    conta: Mapped[str | None] = mapped_column(String(30), nullable=True)
    chave_pix: Mapped[str | None] = mapped_column(String(255), nullable=True)

    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    properties: Mapped[list["Property"]] = relationship(
        "Property", back_populates="owner", cascade="all, delete-orphan"
    )


class Tenant(Base):
    """Inquilino: locatário de um imóvel administrado pela Shalom."""

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    nome: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    cpf_cnpj: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    endereco: Mapped[str | None] = mapped_column(String(500), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    contracts: Mapped[list["Contract"]] = relationship("Contract", back_populates="tenant")


class Property(Base):
    """Imóvel administrado, pertencente a um proprietário."""

    __tablename__ = "properties"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(String(32), ForeignKey("owners.id"), nullable=False, index=True)

    tipo: Mapped[str] = mapped_column(Enum(PropertyType), default=PropertyType.APARTAMENTO, nullable=False)
    status: Mapped[str] = mapped_column(Enum(PropertyStatus), default=PropertyStatus.DISPONIVEL, nullable=False)

    endereco: Mapped[str] = mapped_column(String(500), nullable=False)
    numero: Mapped[str | None] = mapped_column(String(20), nullable=True)
    complemento: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bairro: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cidade: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uf: Mapped[str | None] = mapped_column(String(2), nullable=True)
    cep: Mapped[str | None] = mapped_column(String(15), nullable=True)

    matricula: Mapped[str | None] = mapped_column(String(100), nullable=True)
    valor_iptu_anual: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    valor_condominio: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    owner: Mapped["Owner"] = relationship("Owner", back_populates="properties")
    contracts: Mapped[list["Contract"]] = relationship("Contract", back_populates="property")


class Contract(Base):
    """Contrato de locação: liga um imóvel a um inquilino."""

    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    property_id: Mapped[str] = mapped_column(String(32), ForeignKey("properties.id"), nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(32), ForeignKey("tenants.id"), nullable=False, index=True)

    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[date | None] = mapped_column(Date, nullable=True)
    dia_vencimento: Mapped[int] = mapped_column(default=5, nullable=False)

    valor_aluguel: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    taxa_administracao_percentual: Mapped[float] = mapped_column(Numeric(5, 2), default=10.0, nullable=False)
    indice_reajuste: Mapped[str] = mapped_column(
        Enum(ReadjustmentIndex), default=ReadjustmentIndex.IGPM, nullable=False
    )

    status: Mapped[str] = mapped_column(Enum(ContractStatus), default=ContractStatus.ATIVO, nullable=False)

    fiador_nome: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fiador_cpf: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fiador_telefone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    property: Mapped["Property"] = relationship("Property", back_populates="contracts")
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="contracts")
