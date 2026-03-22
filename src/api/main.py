# src/api/main.py

from fastapi import FastAPI
from src.api.routes import router

app = FastAPI(
    title       = "DPDP Compliance Engine",
    description = "AI-Powered FinTech Compliance & DPDP Regulatory Intelligence System",
    version     = "0.1.0"
)

app.include_router(router)