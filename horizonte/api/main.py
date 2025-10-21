"""Punto de entrada de la API de Horizonte."""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from horizonte.common.config import Settings, get_settings
from horizonte.common.db import init_db
from horizonte.common.logging import RequestLoggingMiddleware, configure_logging
from horizonte.api.routes import audit, health, infer
from horizonte.governance import transparency_api


class PayloadLimitMiddleware(BaseHTTPMiddleware):
    """Middleware que controla el tamaño máximo de los cuerpos de las solicitudes."""

    def __init__(self, app: Any, max_bytes: int) -> None:  # pragma: no cover - probado indirectamente
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_bytes:
            return JSONResponse(status_code=413, content={"detail": "Payload demasiado grande."})
        cuerpo = await request.body()
        if len(cuerpo) > self.max_bytes:
            return JSONResponse(status_code=413, content={"detail": "Payload demasiado grande."})
        request._body = cuerpo  # type: ignore[attr-defined]
        return await call_next(request)


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

    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"], allow_credentials=False)
    app.add_middleware(PayloadLimitMiddleware, max_bytes=settings.max_payload_bytes)
    app.add_middleware(RequestLoggingMiddleware, logger=logger)
    app.add_middleware(SlowAPIMiddleware)

    app.include_router(health.router)
    app.include_router(infer.router)
    app.include_router(audit.router)

    transparencia_router = transparency_api.get_router()
    app.include_router(transparencia_router)

    registrar_manejadores(app, settings, logger)
    return app


def registrar_manejadores(app: FastAPI, settings: Settings, logger: logging.Logger) -> None:
    """Registra manejadores de errores consistentes."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": "Solicitud inválida.", "errors": exc.errors()})

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(status_code=429, content={"detail": "Se excedió el límite de solicitudes."})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = str(uuid4())
        logger.error("error_no_controlado", exc_info=exc, extra={"request_id": request_id})
        return JSONResponse(status_code=500, content={"detail": "Error interno del servidor.", "request_id": request_id})


app = create_app()
