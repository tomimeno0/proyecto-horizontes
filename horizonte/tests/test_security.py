"""Pruebas relacionadas con el middleware de seguridad."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from horizonte.api.main import create_app
from horizonte.common.config import get_settings


@pytest.mark.anyio
async def test_rechaza_payload_excedido(monkeypatch) -> None:
    """La API debe rechazar payloads superiores al máximo configurado."""

    monkeypatch.setenv("MAX_PAYLOAD_BYTES", "10")
    get_settings.cache_clear()
    app = create_app()
    respuesta = None
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            respuesta = await client.post(
                "/inferencia",
                json={"query": "x" * 50},
            )
    finally:
        get_settings.cache_clear()

    assert respuesta is not None
    assert respuesta.status_code == 413
