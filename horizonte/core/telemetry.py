"""Recolección de métricas internas para el núcleo de Horizonte."""

from __future__ import annotations

import time
from collections import deque
from threading import Lock


class TelemetryCollector:
    """Mantiene métricas en memoria para consumo del dashboard interno."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._inferencias_totales = 0
        self._latencia_acumulada = 0.0
        self._latencia_conteo = 0
        self._ethics_denegadas = 0
        self._marcas_tiempo: deque[float] = deque()

    def record_inference(self, latency_ms: float, ethics_denegada: bool) -> None:
        """Registra una inferencia y actualiza las métricas."""
        now = time.time()
        with self._lock:
            self._inferencias_totales += 1
            self._latencia_acumulada += latency_ms
            self._latencia_conteo += 1
            if ethics_denegada:
                self._ethics_denegadas += 1
            self._marcas_tiempo.append(now)
            limite = now - 60
            while self._marcas_tiempo and self._marcas_tiempo[0] < limite:
                self._marcas_tiempo.popleft()

    def reset(self) -> None:
        """Reinicia todas las métricas (uso exclusivo de pruebas)."""
        with self._lock:
            self._inferencias_totales = 0
            self._latencia_acumulada = 0.0
            self._latencia_conteo = 0
            self._ethics_denegadas = 0
            self._marcas_tiempo.clear()

    def snapshot(self) -> dict[str, float | int]:
        """Obtiene una copia de las métricas actuales."""
        with self._lock:
            inferencias = self._inferencias_totales
            denegadas = self._ethics_denegadas
            conteo_latencia = self._latencia_conteo
            latencia_promedio = (
                self._latencia_acumulada / conteo_latencia if conteo_latencia else 0.0
            )
            consultas_minuto = len(self._marcas_tiempo)
        return {
            "inferencias_totales": inferencias,
            "respuestas_ethics_denegadas": denegadas,
            "promedio_latencia_ms": round(latencia_promedio, 2),
            "consultas_por_minuto": consultas_minuto,
        }


def get_metrics() -> dict[str, float | int]:
    """Devuelve las métricas actuales para el dashboard."""
    return telemetry.snapshot()


def record_inference(latency_ms: float, ethics_denegada: bool) -> None:
    """Proxy conveniente para registrar inferencias."""
    telemetry.record_inference(latency_ms, ethics_denegada)


telemetry = TelemetryCollector()
