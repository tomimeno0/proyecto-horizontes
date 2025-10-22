"""Módulo de telemetría en memoria para el proyecto Horizonte."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock


@dataclass
class _MetricsSnapshot:
    inferencias_totales: int
    consultas_por_minuto: int
    respuestas_ethics_denegadas: int
    promedio_latencia_ms: float


class TelemetryCollector:
    """Recolector en memoria de métricas críticas."""

    def __init__(self) -> None:
        self._inferencias_totales = 0
        self._respuestas_ethics_denegadas = 0
        self._latency_sum = 0.0
        self._latency_count = 0
        self._lock = Lock()
        self._request_times: deque[datetime] = deque()

    def record_inference(self, latency_ms: float, ethics_denied: bool = False) -> None:
        """Registra una inferencia con su latencia y estado ético."""

        now = datetime.utcnow()
        with self._lock:
            self._inferencias_totales += 1
            self._latency_sum += max(latency_ms, 0.0)
            self._latency_count += 1
            if ethics_denied:
                self._respuestas_ethics_denegadas += 1
            self._purge_old(now)
            self._request_times.append(now)

    def record_query(self) -> None:
        """Registra una consulta genérica para el cálculo por minuto."""

        now = datetime.utcnow()
        with self._lock:
            self._purge_old(now)
            self._request_times.append(now)

    def _purge_old(self, now: datetime) -> None:
        limite = now - timedelta(minutes=1)
        while self._request_times and self._request_times[0] < limite:
            self._request_times.popleft()

    def snapshot(self) -> _MetricsSnapshot:
        with self._lock:
            promedio = self._latency_sum / self._latency_count if self._latency_count else 0.0
            self._purge_old(datetime.utcnow())
            return _MetricsSnapshot(
                inferencias_totales=self._inferencias_totales,
                consultas_por_minuto=len(self._request_times),
                respuestas_ethics_denegadas=self._respuestas_ethics_denegadas,
                promedio_latencia_ms=round(promedio, 2),
            )


_COLLECTOR = TelemetryCollector()


def record_inference(latency_ms: float, ethics_denied: bool = False) -> None:
    """API pública para registrar inferencias."""

    _COLLECTOR.record_inference(latency_ms, ethics_denied)


def record_query() -> None:
    """API pública para contabilizar consultas sin inferencia."""

    _COLLECTOR.record_query()


def get_metrics() -> dict[str, float | int]:
    """Devuelve las métricas actuales para el dashboard."""

    snapshot = _COLLECTOR.snapshot()
    return {
        "inferencias_totales": snapshot.inferencias_totales,
        "consultas_por_minuto": snapshot.consultas_por_minuto,
        "respuestas_ethics_denegadas": snapshot.respuestas_ethics_denegadas,
        "promedio_latencia_ms": snapshot.promedio_latencia_ms,
    }


__all__ = ["get_metrics", "record_inference", "record_query", "TelemetryCollector"]
