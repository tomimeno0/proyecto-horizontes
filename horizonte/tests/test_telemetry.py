"""Pruebas unitarias para la telemetría interna."""

from __future__ import annotations

from horizonte.core.telemetry import get_metrics, record_inference, telemetry


def test_telemetry_actualiza_metricas() -> None:
    telemetry.reset()
    record_inference(100.0, False)
    record_inference(200.0, True)

    metrics = get_metrics()

    assert metrics["inferencias_totales"] == 2
    assert metrics["respuestas_ethics_denegadas"] == 1
    assert metrics["promedio_latencia_ms"] == 150.0
    assert metrics["consultas_por_minuto"] >= 2
