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
        self._divergencia_total = 0.0
        self._divergencia_muestras = 0
        self._ultima_divergencia = 0.0
        self._consistencia_global = 1.0
        self._consistencia_colectiva = 1.0
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
            self._divergencia_total = 0.0
            self._divergencia_muestras = 0
            self._ultima_divergencia = 0.0
            self._consistencia_global = 1.0
            self._consistencia_colectiva = 1.0
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
            if self._divergencia_muestras:
                divergence_avg = self._divergencia_total / self._divergencia_muestras
            else:
                divergence_avg = 0.0
            divergence_avg = round(divergence_avg, 3)
            global_consistency = round(self._consistencia_global, 3)
            collective = round(self._consistencia_colectiva, 3)
            ciclos = self._ciclos_auto_eval
        return {
            "inferencias_totales": inferencias,
            "respuestas_ethics_denegadas": denegadas,
            "promedio_latencia_ms": round(latencia_promedio, 2),
            "consultas_por_minuto": consultas_minuto,
            "divergence_index_promedio": divergence_avg,
            "consistencia_global": global_consistency,
            "consistencia_colectiva": collective,
            "ciclos_auto_eval": ciclos,
        }

    def record_cognitive_divergence(self, divergence: float) -> None:
        """Acumula el índice de divergencia calculado por metacognición."""

        with self._lock:
            self._divergencia_total += float(divergence)
            self._divergencia_muestras += 1
            self._ultima_divergencia = float(divergence)

    def record_cognitive_cycle(self, consistency: float) -> None:
        """Registra el resultado de un ciclo de autoevaluación."""

        with self._lock:
            self._consistencia_global = float(consistency)
            self._ciclos_auto_eval += 1

    def update_collective_consistency(self, score: float | None) -> None:
        """Almacena la consistencia agregada obtenida de la red."""

        with self._lock:
            self._consistencia_colectiva = 1.0 if score is None else float(score)


def get_metrics() -> dict[str, float | int | dict[str, object]]:
    """Devuelve las métricas actuales para el dashboard."""
    base_metrics = telemetry.snapshot()
    metrics: dict[str, float | int | dict[str, object]] = {}
    for key, value in base_metrics.items():
        metrics[key] = value
    adaptive = get_adaptive_trainer().export_metrics()
    metrics["ethics_adaptive"] = cast(dict[str, object], adaptive)
    return metrics


def record_inference(latency_ms: float, ethics_denegada: bool) -> None:
    """Proxy conveniente para registrar inferencias."""
    telemetry.record_inference(latency_ms, ethics_denegada)


def record_cognitive_divergence(divergence: float) -> None:
    """Proxy para registrar un índice de divergencia cognitiva."""

    telemetry.record_cognitive_divergence(divergence)


def record_cognitive_cycle(consistency: float) -> None:
    """Proxy que acumula la consistencia tras una autoevaluación."""

    telemetry.record_cognitive_cycle(consistency)


def update_collective_consistency(score: float | None) -> None:
    """Proxy para sincronizar la consistencia colectiva distribuida."""

    telemetry.update_collective_consistency(score)


telemetry = TelemetryCollector()
