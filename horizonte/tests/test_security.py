"""Pruebas para los componentes de seguridad."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from horizonte.api.middleware.security import SecurityMiddleware
from horizonte.common.security import hash_text_sha256, sanitize_input


def _build_app(max_bytes: int = 32) -> FastAPI:
    app = FastAPI()
    logger = logging.getLogger("test-security")
    logger.setLevel(logging.DEBUG)
    app.add_middleware(
        SecurityMiddleware,
        max_payload_bytes=max_bytes,
        node_id="nodo-prueba",
        logger=logger,
    )

    @app.post("/echo")
    async def echo(
        payload: dict[str, object],
    ) -> dict[str, object]:  # pragma: no cover - indirecto
        return payload

    return app


def test_payload_demasiado_grande_retorna_413() -> None:
    app = _build_app(max_bytes=10)
    client = TestClient(app)

    response = client.post("/echo", json={"texto": "x" * 50})

    assert response.status_code == 413
    assert response.headers["X-Node-ID"] == "nodo-prueba"


def test_sanitize_input_normaliza_texto() -> None:
    texto = "hola\x00 mundo\u200b  seguro\n"
    assert sanitize_input(texto) == "hola mundo seguro"


def test_hash_text_sha256_reproduce_hash_conocido() -> None:
    assert (
        hash_text_sha256("seguridad")
        == "1ea9f394f510e2beb43cb0b317258b09bce9f4fccef69407360483690ac9b746"
    )
