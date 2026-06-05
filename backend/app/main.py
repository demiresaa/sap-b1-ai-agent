"""FastAPI entry point — SAP B1 AI Agent."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.api.middleware.tenant import TenantResolverMiddleware
from app.api.routes import admin, analytics, auth, debug, documents, orders, sap
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.metrics import metrics_response
from app.core.middleware import RateLimitMiddleware, RequestContextMiddleware
from app.core.observability import init_otel, init_sentry
from app.sap import SAPError, pool

configure_logging(level="INFO", json_format=settings.app_env != "development")
logger = logging.getLogger(__name__)

init_sentry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SAP B1 AI Agent başlatılıyor — env=%s", settings.app_env)
    yield
    await pool.close_all()


app = FastAPI(
    title="SAP B1 AI Agent",
    version="0.1.0",
    description="PDF/e-posta → multi-agent AI → SAP B1 Service Layer.",
    lifespan=lifespan,
)

init_otel(app)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(TenantResolverMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"
    if settings.app_env != "production"
    else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_private_network=True,
)


@app.exception_handler(SAPError)
async def sap_error_handler(_: Request, exc: SAPError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code or 502,
        content={"detail": exc.message_tr, "sap_code": exc.code},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": "İstek doğrulanamadı.", "errors": exc.errors()},
    )


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "sap-b1-ai-agent",
        "version": "0.1.0",
        "env": settings.app_env,
    }


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    body, content_type = metrics_response()
    return Response(content=body, media_type=content_type)


app.include_router(auth.router, prefix="/api/auth")
app.include_router(documents.router, prefix="/api/documents")
app.include_router(orders.router, prefix="/api/orders")
app.include_router(sap.router, prefix="/api/sap")
app.include_router(analytics.router, prefix="/api/analytics")
app.include_router(debug.router, prefix="/api/debug")
app.include_router(admin.router, prefix="/api/admin")
