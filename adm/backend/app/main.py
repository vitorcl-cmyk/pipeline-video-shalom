"""Shalom ADM — API de administração de locação.

Cadastros essenciais: proprietários, inquilinos, imóveis e contratos de
locação. Módulos futuros (cobrança, conciliação bancária) serão adicionados
como novos routers sem alterar esta base.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import auth, billing, charges, contracts, dashboard, ficha, owners, properties, tenants, users

logging.basicConfig(level=logging.INFO)

init_db()

app = FastAPI(title="Shalom ADM API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(owners.router)
app.include_router(tenants.router)
app.include_router(properties.router)
app.include_router(contracts.router)
app.include_router(charges.router)
app.include_router(billing.router)
app.include_router(dashboard.router)
app.include_router(ficha.router)


@app.get("/health")
def health():
    return {"status": "ok"}
