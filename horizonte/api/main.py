"""Punto de entrada de la API de Horizonte."""

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from governance.dashboard.main import router as dashboard_router
from horizonte.api.middleware import SecurityMiddleware
from horizonte.api.routes import audit, health, infer
from horizonte.common.config import Settings, get_settings
from horizonte.common.db import init_db
from horizonte.common.logging import RequestLoggingMiddleware, configure_logging
from horizonte.governance import transparency_api
from horizonte.governance.dashboard import metrics as metrics_router
from net.node_registry import router as nodes_router


def create_app() -> FastAPI:
    """Crea y configura la instancia de FastAPI."""
    settings = get_settings()
    logger = configure_logging(settings)
    init_db()

    limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])

    app = FastAPI(title=settings.app_name)
    app.state.settings = settings
    app.state.logger = logger
    app.state.limiter = limiter

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )
    app.add_middleware(SecurityMiddleware, settings=settings, logger=logger)
    app.add_middleware(RequestLoggingMiddleware, logger=logger)
    app.add_middleware(SlowAPIMiddleware)

    app.include_router(health.router)
    app.include_router(infer.router)
    app.include_router(audit.router)
    app.include_router(nodes_router, prefix="/nodes")
    app.include_router(metrics_router.router, prefix="/metrics")

    transparencia_router = transparency_api.get_router()
    app.include_router(transparencia_router)
    app.mount("/dashboard", dashboard_router)

    registrar_manejadores(app, settings, logger)
    return app


def registrar_manejadores(app: FastAPI, settings: Settings, logger: logging.Logger) -> None:
    """Registra manejadores de errores consistentes."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid4()))
        logger.warning(
            "validacion_invalida",
            extra={"request_id": request_id, "error": exc.errors()},
        )
        return JSONResponse(
            status_code=400,
            content={"detail": "Solicitud inválida.", "errors": exc.errors()},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid4()))
        logger.warning(
            "valor_invalido",
            extra={"request_id": request_id, "error": str(exc)},
        )
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        request_id = getattr(request.state, "request_id", str(uuid4()))
        logger.warning(
            "rate_limit_excedido",
            extra={"request_id": request_id, "error": str(exc)},
        )
        return JSONResponse(
            status_code=429, content={"detail": "Se excedió el límite de solicitudes."}
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = str(uuid4())
        logger.error("error_no_controlado", exc_info=exc, extra={"request_id": request_id})
        return JSONResponse(
            status_code=500,
            content={"detail": "Error interno del servidor.", "request_id": request_id},
        )


app = create_app()
