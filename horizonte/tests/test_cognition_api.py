"""Pruebas para los endpoints de cognición."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from httpx import ASGITransport, AsyncClient

from horizonte.api.main import app
from horizonte.common.db import Base, engine
from horizonte.core.metacognition import CognitiveMirror, set_cognitive_mirror
from horizonte.net.cognitive_sync import (
    CognitiveSyncManager,
    set_cognitive_sync_manager,
)


@pytest.fixture(autouse=True)
def preparar_ledger() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    set_cognitive_mirror(None)
    set_cognitive_sync_manager(None)


@pytest.mark.anyio("asyncio")
async def test_endpoints_cognition(tmp_path) -> None:
    """Los endpoints deben exponer el estado y permitir reinicios."""

    mirror = CognitiveMirror(
        inference_func=lambda q: "respuesta",
        log_path=tmp_path / "cognitive_log.json",
    )
    set_cognitive_mirror(mirror)
    manager = CognitiveSyncManager(
        node_id="nodo-prueba",
        mirror=mirror,
        peer_score_provider=lambda count: [0.8, 0.85, 0.9],
        log_path=tmp_path / "sync_log.json",
        threshold=0.7,
    )
    set_cognitive_sync_manager(manager)
    manager.run_cycle()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        estado = await client.get("/cognition/status")
        assert estado.status_code == 200
        payload = estado.json()
        assert "mirror" in payload and "network" in payload

        historial = await client.get("/cognition/history")
        assert historial.status_code == 200
        assert isinstance(historial.json(), list)

        recheck = await client.post("/cognition/recheck")
        assert recheck.status_code == 200
        assert "status" in recheck.json()

        reset = await client.delete("/cognition/reset")
        assert reset.status_code == 204
