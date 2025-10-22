"""Pruebas de la ruta de auditoría."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from httpx import ASGITransport, AsyncClient

from horizonte.api.main import app
from horizonte.common.db import Base, engine


@pytest.fixture(autouse=True)
def limpiar_ledger() -> Generator[None, None, None]:
    """Reinicia la base de datos antes de cada prueba."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.mark.anyio("asyncio")
async def test_auditoria_lista_registros() -> None:
    """La auditoría debe listar los registros generados."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for idx in range(3):
            await client.post("/inferencia", json={"query": f"Consulta {idx}"})
        respuesta = await client.get("/auditoria")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    hashes = {item["hash"] for item in cuerpo["items"]}
    assert len(hashes) == len(cuerpo["items"]) == 3
