"""Configuración de logging estructurado para Horizonte."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from .config import Settings


class JsonFormatter(logging.Formatter):
    """Formateador que emite logs estructurados en formato JSON."""

    _RESERVED_KEYS = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
    }

    def __init__(self, node_id: str) -> None:
        super().__init__()
        self.node_id = node_id

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
            "node_id": self.node_id,
        }
        for optional_key in ("request_id", "latency_ms"):
            value = getattr(record, optional_key, None)
            if value is not None:
                payload[optional_key] = value
        for key, value in record.__dict__.items():
            if key in self._RESERVED_KEYS or key in payload:
                continue
            if key.startswith("_"):
                continue
            payload[key] = value
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

    def __init__(self, app: Any, logger: logging.Logger) -> None:  # pragma: no cover
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        inicio = time.perf_counter()
        response = await call_next(request)
        duracion_ms = (time.perf_counter() - inicio) * 1000
        extra: dict[str, Any] = {
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "latency_ms": round(duracion_ms, 2),
        }
        request_id = request.headers.get("x-request-id")
        if request_id:
            extra["request_id"] = request_id
        self.logger.info("request", extra=extra)
        return response
