"""Configuración de logging estructurado para Horizonte."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from .config import Settings


class JsonFormatter(logging.Formatter):
    """Formateador que emite logs en JSON."""

    def __init__(self, node_id: str) -> None:
        super().__init__()
        self.node_id = node_id

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.name,
            "node_id": self.node_id,
        }
        extra_keys = {"method", "path", "status", "ms"}
        for key in extra_keys:
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["error"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(settings: Settings) -> logging.Logger:
    """Configura el logger raíz con formato JSON."""
    logger = logging.getLogger()
    logger.setLevel(settings.log_level)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(node_id=settings.node_id))
    logger.handlers = [handler]
    logger.propagate = False
    return logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware que registra cada solicitud entrante."""

    def __init__(self, app: Any, logger: logging.Logger) -> None:  # pragma: no cover - se valida en integración
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        inicio = time.perf_counter()
        response = await call_next(request)
        duracion_ms = (time.perf_counter() - inicio) * 1000
        self.logger.info(
            "request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "ms": round(duracion_ms, 2),
            },
        )
        return response
