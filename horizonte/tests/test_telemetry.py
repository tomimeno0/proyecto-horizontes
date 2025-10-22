"""Pruebas unitarias para el recolector de telemetría."""

from __future__ import annotations

from horizonte.core.telemetry import TelemetryCollector


def test_telemetry_snapshot() -> None:
    """El recolector debe calcular correctamente las métricas agregadas."""

    collector = TelemetryCollector()
    collector.record_inference(100.0)
    collector.record_inference(200.0, ethics_denied=True)
    collector.record_query()

    snapshot = collector.snapshot()

    assert snapshot.inferencias_totales == 2
    assert snapshot.respuestas_ethics_denegadas == 1
    assert snapshot.consultas_por_minuto == 3
    assert snapshot.promedio_latencia_ms == 150.0
