import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Open-Source Arabic Enterprise Finance Document AI Platform API",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# ── CORS ────────────────────────────────────────────────────────────────────
# Restrict allowed origins to the frontend domain only.
# Override via ALLOWED_ORIGINS env var (comma-separated) for production.
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000"
)
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Prometheus Metrics ───────────────────────────────────────────────────────
# Exposes /metrics endpoint consumed by Prometheus scraper.
Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_respect_env_var=False,
    excluded_handlers=["/health", "/metrics"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# ── Routers ──────────────────────────────────────────────────────────────────
from app.api.api import api_router  # noqa: E402 (import after app creation)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health"])
def root():
    return {"message": "Arabic Enterprise Finance Document AI Platform API", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
