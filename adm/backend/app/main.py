"""Shalom ADM — API de administração de locação.

Cadastros essenciais: proprietários, inquilinos, imóveis e contratos de
locação. Módulos futuros (cobrança, conciliação bancária) serão adicionados
como novos routers sem alterar esta base.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth, charges, contracts, dashboard, owners, properties, tenants

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Shalom ADM API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(owners.router)
app.include_router(tenants.router)
app.include_router(properties.router)
app.include_router(contracts.router)
app.include_router(charges.router)
app.include_router(dashboard.router)


@app.get("/health")
def health():
    return {"status": "ok"}
