"""SQLAlchemy engine, session factory and declarative base."""
import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

logger = logging.getLogger("database")

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Cria tabelas novas e adiciona colunas novas em tabelas que já
    existem (sem Alembic: `Base.metadata.create_all` só cria tabela que
    ainda não existe, nunca faz ALTER TABLE em tabela existente — sem
    isso, toda vez que um campo novo é adicionado a um model, o deploy
    quebra em produção com "no such column" até alguém arrumar o banco
    na mão)."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue  # tabela nova: create_all() abaixo já cria com todas as colunas
            existing_columns = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                logger.warning("Migração: adicionando coluna %s.%s (%s)", table.name, column.name, col_type)
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}'))

    Base.metadata.create_all(bind=engine)
