"""Pruebas para el monitor ético adaptativo y sus endpoints."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from horizonte.api.routes import ethics_audit
from horizonte.core import ethics_filter
from horizonte.core.adaptive_learning import AdaptiveTrainer
from horizonte.core.ethics_monitor import EthicsMonitor, set_ethics_monitor


@pytest.mark.anyio
async def test_ethics_monitor_generates_alert(tmp_path) -> None:
    cache_path = tmp_path / "cache.json"
    audit_path = tmp_path / "audit.json"
    trainer = AdaptiveTrainer(cache_path=cache_path, buffer_size=20)

    for idx in range(4):
        trainer.log_inference(
            query=f"consulta-{idx}",
            response_hash=f"hash-{idx}",
            flags=["posible_sesgo"],
            response_time_ms=20.0,
            allowed=False,
        )

    monitor = EthicsMonitor(trainer=trainer, audit_path=audit_path)
    snapshot = await monitor.poll()

    assert snapshot["alert"] == "degradacion_moral"
    logs = monitor.get_audit_logs()
    assert logs
    assert logs[-1]["alert"] == "degradacion_moral"


def test_ethics_metrics_endpoint(tmp_path) -> None:
    cache_path = tmp_path / "cache.json"
    audit_path = tmp_path / "audit.json"
    trainer = AdaptiveTrainer(cache_path=cache_path, buffer_size=10)
    ethics_filter.set_adaptive_trainer_override(trainer)
    monitor = EthicsMonitor(trainer=trainer, audit_path=audit_path)
    set_ethics_monitor(monitor)

    app = FastAPI()
    app.include_router(ethics_audit.router)
    client = TestClient(app)

    trainer.log_inference(
        query="consulta",
        response_hash="hash",
        flags=[],
        response_time_ms=10.0,
        allowed=True,
    )

    response = client.get("/ethics/metrics")
    assert response.status_code == 200
    data = response.json()
    assert {"precision", "consistency", "bias_index"} <= data.keys()

    set_ethics_monitor(None)
    ethics_filter.set_adaptive_trainer_override(None)
