"""Recolección de métricas internas para el núcleo de Horizonte."""

from __future__ import annotations

import time
from collections import deque
from threading import Lock
from typing import cast

from horizonte.core.adaptive_learning import get_adaptive_trainer


class TelemetryCollector:
    """Mantiene métricas en memoria para consumo del dashboard interno."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._inferencias_totales = 0
        self._latencia_acumulada = 0.0
        self._latencia_conteo = 0
        self._ethics_denegadas = 0
        self._marcas_tiempo: deque[float] = deque()
        self._divergence_sum = 0.0
        self._divergence_count = 0
        self._consistencia_global = 1.0
        self._ciclos_auto_eval = 0

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
            self._divergence_sum = 0.0
            self._divergence_count = 0
            self._consistencia_global = 1.0
            self._ciclos_auto_eval = 0

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
            divergence_promedio = (
                self._divergence_sum / self._divergence_count if self._divergence_count else 0.0
            )
            consistencia_global = self._consistencia_global
            ciclos_auto_eval = self._ciclos_auto_eval
        return {
            "inferencias_totales": inferencias,
            "respuestas_ethics_denegadas": denegadas,
            "promedio_latencia_ms": round(latencia_promedio, 2),
            "consultas_por_minuto": consultas_minuto,
            "divergence_index_promedio": round(divergence_promedio, 3),
            "consistencia_global": round(consistencia_global, 3),
            "ciclos_auto_eval": ciclos_auto_eval,
        }

    def record_cognitive_divergence(self, divergence: float) -> None:
        with self._lock:
            self._divergence_sum += float(divergence)
            self._divergence_count += 1

    def register_auto_evaluation(self, consistency: float) -> None:
        with self._lock:
            self._consistencia_global = float(consistency)
            self._ciclos_auto_eval += 1


def get_metrics() -> dict[str, float | int | dict[str, object]]:
    """Devuelve las métricas actuales para el dashboard."""
    snapshot = telemetry.snapshot()
    metrics: dict[str, float | int | dict[str, object]] = dict(snapshot)
    metrics["ethics_adaptive"] = cast(dict[str, object], get_adaptive_trainer().export_metrics())
    return metrics


def record_inference(latency_ms: float, ethics_denegada: bool) -> None:
    """Proxy conveniente para registrar inferencias."""
    telemetry.record_inference(latency_ms, ethics_denegada)


def record_cognitive_divergence(divergence: float) -> None:
    """Registra la divergencia cognitiva observada en una inferencia."""

    telemetry.record_cognitive_divergence(divergence)


def register_auto_evaluation(consistency: float) -> None:
    """Registra el resultado de una autoevaluación cognitiva."""

    telemetry.register_auto_evaluation(consistency)


telemetry = TelemetryCollector()
