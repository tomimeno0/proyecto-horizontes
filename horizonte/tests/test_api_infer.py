"""Pruebas de la ruta de inferencia."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from horizonte.api.main import app
from horizonte.common.db import Base, Ledger, engine, get_session


@pytest.fixture(autouse=True)
def limpiar_ledger() -> None:
    """Reinicia la base de datos antes de cada prueba."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.mark.anyio
async def test_inferencia_exitosa() -> None:
    """La ruta debe responder con datos completos."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        respuesta = await client.post("/inferencia", json={"query": "¿Impacto?"})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert {"query", "response", "hash", "timestamp", "ethics"} <= cuerpo.keys()
    with get_session() as session:
        total = session.execute(select(func.count()).select_from(Ledger)).scalar_one()
        assert total == 1


@pytest.mark.anyio
async def test_inferencia_query_vacia() -> None:
    """Una consulta vacía debe generar error 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        respuesta = await client.post("/inferencia", json={"query": ""})
    assert respuesta.status_code == 400
