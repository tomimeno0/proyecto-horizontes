"""Middlewares de seguridad para la API de Horizonte."""

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from horizonte.common.config import Settings
from horizonte.common.security import sanitize_input


class SecurityMiddleware(BaseHTTPMiddleware):
    """Middleware que aplica controles de seguridad básicos."""

    def __init__(
        self, app: ASGIApp, settings: Settings, logger: logging.Logger
    ) -> None:
        super().__init__(app)
        self._max_payload = settings.max_payload_bytes
        self._node_id = settings.node_id
        self._logger = logger

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        request_id = request.headers.get("x-request-id", str(uuid4()))
        request.state.request_id = request_id

        content_length_header = request.headers.get("content-length")
        if content_length_header:
            try:
                if int(content_length_header) > self._max_payload:
                    self._logger.warning(
                        "payload_rechazado",
                        extra={
                            "request_id": request_id,
                            "reason": "content_length_exceeded",
                        },
                    )
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Payload demasiado grande."},
                    )
            except ValueError:
                # Ignorar headers inválidos, se validará leyendo el cuerpo.
                pass

        raw_body = await request.body()
        if len(raw_body) > self._max_payload:
            self._logger.warning(
                "payload_rechazado",
                extra={"request_id": request_id, "reason": "body_exceeded"},
            )
            return JSONResponse(
                status_code=413, content={"detail": "Payload demasiado grande."}
            )

        content_type = request.headers.get("content-type", "")
        if raw_body and ("json" in content_type or content_type.startswith("text/")):
            try:
                decoded_body = raw_body.decode("utf-8")
            except UnicodeDecodeError:
                self._logger.warning(
                    "payload_rechazado",
                    extra={"request_id": request_id, "reason": "invalid_encoding"},
                )
                return JSONResponse(
                    status_code=400,
                    content={"detail": "Entrada no válida."},
                )

            sanitized = sanitize_input(decoded_body)
            request.state.sanitized_body = sanitized

        request._body = raw_body  # type: ignore[attr-defined]

        response = await call_next(request)
        response.headers["X-Node-ID"] = self._node_id
        return response


__all__ = ["SecurityMiddleware"]
