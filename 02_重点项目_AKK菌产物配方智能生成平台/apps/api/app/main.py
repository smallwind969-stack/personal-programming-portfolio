import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import akk_products, experiments, formula, health, knowledge, llm, system

app = FastAPI(title="AKK Formula API", version="0.1.0")

cors_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
cors_origins = [origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()]
cors_origin_regex = os.getenv(
    "CORS_ORIGIN_REGEX",
    r"^(http://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+):3000|https://[a-z0-9-]+\.vercel\.app)$",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(akk_products.router)
app.include_router(formula.router)
app.include_router(knowledge.router)
app.include_router(llm.router)
app.include_router(experiments.router)
app.include_router(system.router)
