"""Módulo de metacognición y autoevaluación para AUREUS."""

from __future__ import annotations

import asyncio
import json
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Callable

from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from horizonte.common.db import Ledger, get_session


@dataclass(frozen=True)
class CognitiveSnapshot:
    """Estado resumido del espejo cognitivo."""

    divergence_index: float
    last_divergence: float
    consistency_score: float
    auto_eval_cycles: int
    last_self_check: str | None


class CognitiveMirror:
    """Genera subcogniciones y evalúa la coherencia interna del sistema."""

    def __init__(
        self,
        inference_func: Callable[[str], str],
        log_path: Path | None = None,
        subcognition_factories: Sequence[Callable[[str], str]] | None = None,
        divergence_threshold: float = 0.4,
        max_logs: int = 500,
    ) -> None:
        self._inference_func = inference_func
        self._log_path = log_path or Path(__file__).resolve().parent / "cognitive_log.json"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._log_path.exists():
            self._log_path.write_text("[]", encoding="utf-8")
        self._lock = Lock()
        self._divergence_sum = 0.0
        self._divergence_count = 0
        self._last_divergence = 0.0
        self._consistency_score = 1.0
        self._auto_eval_cycles = 0
        self._last_self_check: str | None = None
        self._factories = list(subcognition_factories or [])
        self._divergence_threshold = float(divergence_threshold)
        self._max_logs = max(1, max_logs)

    # ------------------------------------------------------------------
    # Generación y evaluación de subcogniciones
    # ------------------------------------------------------------------
    def evaluate(self, query: str, total: int = 3) -> dict[str, object]:
        """Genera subcogniciones, calcula divergencia y registra la decisión."""

        subcognitions = list(self._generate_subcognitions(query, total))
        divergence = self._calculate_divergence(subcognitions)
        final_response, reevaluated = self._majority_reasoning(subcognitions, divergence)
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = {
            "type": "inference",
            "timestamp": timestamp,
            "query": query,
            "subcognitions": subcognitions,
            "divergence_index": round(divergence, 3),
            "final_response": final_response,
            "reevaluated": reevaluated,
        }
        with self._lock:
            self._last_divergence = float(divergence)
            self._divergence_sum += float(divergence)
            self._divergence_count += 1
            self._append_log(entry)
        self._record_divergence_metric(divergence)
        return {
            "final_response": final_response,
            "divergence_index": divergence,
            "reevaluated": reevaluated,
            "subcognitions": subcognitions,
            "timestamp": timestamp,
        }

    def _generate_subcognitions(self, query: str, total: int) -> Iterable[str]:
        if self._factories:
            for factory in self._factories:
                yield factory(query)
            if len(self._factories) >= total:
                return
        remaining = max(0, total - len(self._factories))
        for _ in range(remaining):
            yield self._inference_func(query)

    @staticmethod
    def _calculate_divergence(responses: Sequence[str]) -> float:
        if len(responses) <= 1:
            return 0.0
        unique = len({resp.strip() for resp in responses})
        if unique <= 1:
            return 0.0
        return (unique - 1) / (len(responses) - 1)

    def _majority_reasoning(self, responses: Sequence[str], divergence: float) -> tuple[str, bool]:
        counter = Counter(responses)
        if not counter:
            return "", False
        most_common = counter.most_common()
        final_response = most_common[0][0]
        reevaluated = False
        if divergence > self._divergence_threshold:
            reevaluated = True
            top_count = most_common[0][1]
            empatados = [resp for resp, count in most_common if count == top_count]
            if len(empatados) > 1:
                # Si no hay mayoría clara, se solicita una nueva inferencia
                final_response = self._inference_func(" ".join(sorted(set(responses))))
            else:
                final_response = most_common[0][0]
        return final_response, reevaluated

    # ------------------------------------------------------------------
    # Autoevaluación
    # ------------------------------------------------------------------
    def analyze_self(self, sample_size: int = 50) -> float:
        """Evalúa la coherencia del ledger reciente y registra el resultado."""

        with get_session() as session:
            stmt = (
                select(Ledger.query, Ledger.response).order_by(Ledger.id.desc()).limit(sample_size)
            )
            try:
                rows = session.execute(stmt).all()
            except OperationalError:
                rows = []
        if not rows:
            score = 1.0
        else:
            total = len(rows)
            grouped: dict[str, Counter[str]] = {}
            for query, response in rows:
                grouped.setdefault(query, Counter())[response] += 1
            consistent = 0
            for counter in grouped.values():
                consistent += counter.most_common(1)[0][1]
            score = consistent / total
        score = round(score, 3)
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = {
            "type": "self_check",
            "timestamp": timestamp,
            "consistency_score": score,
            "sample_size": sample_size,
        }
        with self._lock:
            self._consistency_score = score
            self._auto_eval_cycles += 1
            self._last_self_check = timestamp
            self._append_log(entry)
        self._record_auto_eval_metric(score)
        return score

    # ------------------------------------------------------------------
    # Logs y métricas
    # ------------------------------------------------------------------
    def _append_log(self, entry: dict[str, object]) -> None:
        try:
            data = json.loads(self._log_path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                data = []
        except json.JSONDecodeError:
            data = []
        data.append(entry)
        data = data[-self._max_logs :]
        self._log_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def history(self, limit: int | None = None) -> list[dict[str, object]]:
        try:
            data = json.loads(self._log_path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return []
        except json.JSONDecodeError:
            return []
        if limit is None:
            return data
        return data[-limit:]

    def reset_logs(self) -> None:
        with self._lock:
            self._log_path.write_text("[]", encoding="utf-8")
            self._divergence_sum = 0.0
            self._divergence_count = 0
            self._consistency_score = 1.0
            self._auto_eval_cycles = 0
            self._last_self_check = None
            self._last_divergence = 0.0

    def snapshot(self) -> CognitiveSnapshot:
        with self._lock:
            average = (
                self._divergence_sum / self._divergence_count if self._divergence_count else 0.0
            )
            return CognitiveSnapshot(
                divergence_index=round(average, 3),
                last_divergence=round(self._last_divergence, 3),
                consistency_score=self._consistency_score,
                auto_eval_cycles=self._auto_eval_cycles,
                last_self_check=self._last_self_check,
            )

    # ------------------------------------------------------------------
    # Telemetría cooperativa
    # ------------------------------------------------------------------
    def _record_divergence_metric(self, divergence: float) -> None:
        try:
            from horizonte.core.telemetry import record_cognitive_divergence

            record_cognitive_divergence(divergence)
        except Exception:  # pragma: no cover - no se desea interrumpir flujo
            pass

    def _record_auto_eval_metric(self, consistency: float) -> None:
        try:
            from horizonte.core.telemetry import register_auto_evaluation

            register_auto_evaluation(consistency)
        except Exception:  # pragma: no cover
            pass


# ----------------------------------------------------------------------
# Gestión global
# ----------------------------------------------------------------------
_MIRROR: CognitiveMirror | None = None


def get_cognitive_mirror() -> CognitiveMirror:
    """Obtiene una instancia global del espejo cognitivo."""

    global _MIRROR
    if _MIRROR is None:
        from horizonte.core.inference_engine import infer

        _MIRROR = CognitiveMirror(inference_func=infer)
    return _MIRROR


def set_cognitive_mirror(mirror: CognitiveMirror | None) -> None:
    global _MIRROR
    _MIRROR = mirror


def record_cognitive_event(
    source: str, event: str, payload: Mapping[str, object] | None = None
) -> None:
    mirror = get_cognitive_mirror()
    payload_dict: dict[str, object] = {}
    if payload:
        payload_dict = {key: value for key, value in payload.items()}
    entry: dict[str, object] = {
        "type": "event",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "event": event,
        "payload": payload_dict,
    }
    with mirror._lock:  # acceso controlado al registro
        mirror._append_log(entry)


async def periodic_self_assessment(interval: float = 600.0) -> None:
    """Ejecuta autoevaluaciones periódicas de manera indefinida."""

    mirror = get_cognitive_mirror()
    while True:
        mirror.analyze_self()
        await asyncio.sleep(interval)


__all__ = [
    "CognitiveMirror",
    "CognitiveSnapshot",
    "get_cognitive_mirror",
    "set_cognitive_mirror",
    "record_cognitive_event",
    "periodic_self_assessment",
]
