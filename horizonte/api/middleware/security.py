"""Middlewares de seguridad para la API de Horizonte."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class SecurityMiddleware(BaseHTTPMiddleware):
    """Aplica controles básicos de seguridad a la API."""

    def __init__(
        self,
        app: Any,
        *,
        max_payload_bytes: int,
        node_id: str,
        logger: logging.Logger,
    ) -> None:
        super().__init__(app)
        self._max_payload_bytes = max_payload_bytes
        self._node_id = node_id
        self._logger = logger

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("x-request-id")
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self._max_payload_bytes:
                    return self._reject_request(
                        "Payload demasiado grande.",
                        status_code=413,
                        request_id=request_id,
                    )
            except ValueError:
                return self._reject_request(
                    "Encabezado Content-Length inválido.",
                    status_code=400,
                    request_id=request_id,
                )

        body = await request.body()
        if len(body) > self._max_payload_bytes:
            return self._reject_request(
                "Payload demasiado grande.", status_code=413, request_id=request_id
            )

        request._body = body  # type: ignore[attr-defined]
        response = await call_next(request)
        response.headers["X-Node-ID"] = self._node_id
        return response

    def _reject_request(
        self, detail: str, *, status_code: int, request_id: str | None
    ) -> JSONResponse:
        extra: dict[str, object] = {"reason": detail}
        if request_id:
            extra["request_id"] = request_id
        self._logger.warning("solicitud_bloqueada", extra=extra)
        response = JSONResponse(status_code=status_code, content={"detail": detail})
        response.headers["X-Node-ID"] = self._node_id
        return response
