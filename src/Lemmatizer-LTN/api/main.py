"""
FastAPI application for the Latin Lemmatizer API.

Run with:
    uvicorn api.main:app --host 127.0.0.1 --port 8000

Environment variables:
    DATABASE_URL   — PostgreSQL connection string
    API_TOKENS     — comma-separated list of valid bearer tokens
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import close_pool, open_pool
from .routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the database connection pool lifecycle."""
    open_pool()
    yield
    close_pool()


app = FastAPI(
    title="Latin Lemmatizer API",
    description=(
        "REST API for querying Latin lemmas and inflected forms. "
        "Backed by a PostgreSQL database; exposed via Cloudflare Tunnel."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the Cloudflare Tunnel origin and local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production if needed
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["Authorization"],
)

app.include_router(router)
