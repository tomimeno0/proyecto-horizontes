"""Punto de entrada de la API de Horizonte."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from governance.dashboard import live as live_dashboard
from governance.dashboard import metrics as metrics_router
from governance.dashboard.main import STATIC_DIR
from governance.dashboard.main import api_router as dashboard_api_router
from governance.routes import votes
from horizonte.api.middleware.security import SecurityMiddleware
from horizonte.api.routes import audit, cognition, ethics_audit, health, infer
from horizonte.common.config import Settings, get_settings
from horizonte.common.db import init_db
from horizonte.common.logging import RequestLoggingMiddleware, configure_logging
from horizonte.core.metacognition import get_cognitive_mirror
from horizonte.governance import transparency_api
from horizonte.net.cognitive_sync import get_cognitive_sync_manager, periodic_cognitive_sync
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
    app.add_middleware(
        SecurityMiddleware,
        max_payload_bytes=settings.max_payload_bytes,
        node_id=settings.node_id,
        logger=logger,
    )
    app.add_middleware(RequestLoggingMiddleware, logger=logger)
    app.add_middleware(SlowAPIMiddleware)

    app.include_router(health.router)
    app.include_router(infer.router)
    app.include_router(audit.router)
    app.include_router(ethics_audit.router)
    app.include_router(cognition.router)
    app.include_router(nodes_router, prefix="/nodes")
    app.include_router(metrics_router.router, prefix="/metrics")
    app.include_router(votes.router, prefix="/governance")
    app.include_router(live_dashboard.router)
    app.include_router(live_dashboard.router, prefix="/dashboard")
    app.include_router(dashboard_api_router, prefix="/dashboard")
    app.mount(
        "/dashboard/static",
        StaticFiles(directory=str(STATIC_DIR)),
        name="dashboard-static",
    )

    transparencia_router = transparency_api.get_router()
    app.include_router(transparencia_router)

    tareas: list[asyncio.Task[None]] = []

    @app.on_event("startup")
    async def start_cognition_tasks() -> None:
        # Inicializa componentes cognitivos y lanza la autoevaluación periódica.
        get_cognitive_mirror()
        get_cognitive_sync_manager()
        tareas.append(asyncio.create_task(periodic_cognitive_sync()))

    @app.on_event("shutdown")
    async def stop_cognition_tasks() -> None:
        for task in tareas:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    registrar_manejadores(app, settings, logger)
    return app


def registrar_manejadores(app: FastAPI, settings: Settings, logger: logging.Logger) -> None:
    """Registra manejadores de errores consistentes."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        extra = {"errors": exc.errors()}
        request_id = request.headers.get("x-request-id")
        if request_id:
            extra["request_id"] = request_id
        logger.error("error_validacion", extra=extra)
        return JSONResponse(
            status_code=400,
            content={"detail": "Solicitud inválida.", "errors": exc.errors()},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        extra = {"detail": str(exc)}
        request_id = request.headers.get("x-request-id")
        if request_id:
            extra["request_id"] = request_id
        logger.error("error_validacion_valor", extra=extra)
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
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
