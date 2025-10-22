"""Módulo de metacognición y autoevaluación cognitiva de Horizonte."""

from __future__ import annotations

import json
from collections import Counter, deque
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any

from sqlalchemy import desc, select

from horizonte.common.db import Ledger, get_session
from horizonte.core import inference_engine


@dataclass(slots=True)
class CognitiveSnapshot:
    """Representa el estado actual de la autoevaluación cognitiva."""

    divergence_index: float
    global_consistency: float
    collective_consistency: float | None
    cycles: int
    last_audit: str | None


SubGenerator = Callable[[str, str, int], Sequence[str]]
LedgerProvider = Callable[[int], Sequence[Any]]


class CognitiveMirror:
    """Genera subcogniciones y evalúa la coherencia interna del sistema."""

    def __init__(
        self,
        *,
        log_path: Path | None = None,
        subinstances: int = 3,
        inference_fn: Callable[[str], str] | None = None,
        ledger_provider: LedgerProvider | None = None,
        subgenerator: SubGenerator | None = None,
        max_log_entries: int = 500,
    ) -> None:
        self.log_path = log_path or Path(__file__).resolve().with_name("cognitive_log.json")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.write_text("[]", encoding="utf-8")
        self.subinstances = max(1, subinstances)
        self._inference_fn = inference_fn or inference_engine.infer
        self._ledger_provider = ledger_provider or self._default_ledger_provider
        self._subgenerator = subgenerator or self._default_subgenerator
        self._max_log_entries = max(10, max_log_entries)
        self._lock = RLock()
        self._divergence_history: deque[float] = deque(maxlen=200)
        self._global_consistency = 1.0
        self._collective_consistency: float | None = None
        self._cycles = 0
        self._last_audit: str | None = None

    # ------------------------------------------------------------------
    # Procesos metacognitivos
    # ------------------------------------------------------------------
    def evaluate(self, query: str, base_response: str | None = None) -> dict[str, object]:
        """Genera subcogniciones y decide la respuesta final."""

        response = base_response or self._inference_fn(query)
        subcognitions = list(self._subgenerator(query, response, self.subinstances))
        candidates = [response, *subcognitions]
        divergence = self._calculate_divergence(candidates)
        selected = response
        strategy = "base"
        if divergence > 0.4:
            selected = self._majority_reasoning(candidates)
            strategy = "majority"
        timestamp = datetime.now(timezone.utc).isoformat()
        log_entry = {
            "timestamp": timestamp,
            "type": "evaluation",
            "query": query,
            "candidates": candidates,
            "selected": selected,
            "divergence_index": divergence,
            "strategy": strategy,
        }
        self._append_log(log_entry)
        with self._lock:
            self._divergence_history.append(divergence)
        self._record_divergence(divergence)
        return {
            "response": selected,
            "divergence_index": divergence,
            "strategy": strategy,
            "candidates": candidates,
            "timestamp": timestamp,
        }

    def analyze_self(self, *, limit: int = 50) -> dict[str, object]:
        """Evalúa la coherencia de las respuestas recientes en el ledger."""

        registros = self._ledger_provider(limit)
        score = self._consistency_score(registros)
        timestamp = datetime.now(timezone.utc).isoformat()
        payload = {
            "timestamp": timestamp,
            "type": "analysis",
            "ledger_sample": min(len(registros), limit),
            "consistency_score": score,
        }
        self._append_log(payload)
        with self._lock:
            self._global_consistency = score
            self._cycles += 1
            self._last_audit = timestamp
        self._record_cycle(score)
        return payload

    # ------------------------------------------------------------------
    # Estado público
    # ------------------------------------------------------------------
    def status(self) -> CognitiveSnapshot:
        """Obtiene un snapshot seguro para exposición externa."""

        with self._lock:
            if self._divergence_history:
                divergence = sum(self._divergence_history) / len(self._divergence_history)
            else:
                divergence = 0.0
            snapshot = CognitiveSnapshot(
                divergence_index=round(divergence, 3),
                global_consistency=round(self._global_consistency, 3),
                collective_consistency=(
                    round(self._collective_consistency, 3)
                    if self._collective_consistency is not None
                    else None
                ),
                cycles=self._cycles,
                last_audit=self._last_audit,
            )
        return snapshot

    def register_event(self, source: str, detail: Mapping[str, Any]) -> None:
        """Registra eventos provenientes de otros módulos cognitivos."""

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "event",
            "source": source,
            "detail": dict(detail),
        }
        self._append_log(entry)

    def update_collective_consistency(self, score: float | None) -> None:
        """Actualiza la consistencia colectiva distribuida."""

        with self._lock:
            self._collective_consistency = None if score is None else float(score)
        if score is not None:
            self._record_collective(score)

    def history(self, limit: int | None = None) -> list[dict[str, object]]:
        """Devuelve las entradas registradas en el log cognitivo."""

        data = self._read_log()
        if limit is not None:
            return data[-limit:]
        return data

    def reset(self) -> None:
        """Borra las trazas registradas y reinicia el estado interno."""

        with self._lock:
            self._divergence_history.clear()
            self._global_consistency = 1.0
            self._collective_consistency = None
            self._cycles = 0
            self._last_audit = None
        self.log_path.write_text("[]", encoding="utf-8")
        self._record_collective(None)

    def stream_payload(self) -> dict[str, object]:
        """Construye el payload periódico para el dashboard."""

        snapshot = self.status()
        return {
            "divergence_index": snapshot.divergence_index,
            "global_consistency": snapshot.global_consistency,
            "collective_consistency": snapshot.collective_consistency,
            "cycles": snapshot.cycles,
            "last_audit": snapshot.last_audit,
        }

    # ------------------------------------------------------------------
    # Internos de cálculo
    # ------------------------------------------------------------------
    def _default_subgenerator(self, query: str, response: str, subinstances: int) -> Sequence[str]:
        """Genera variantes deterministas rotando tokens."""

        tokens = response.split()
        if not tokens:
            return []
        variants = []
        for offset in range(1, subinstances + 1):
            rotation = offset % len(tokens)
            rotated = tokens[rotation:] + tokens[:rotation]
            variants.append(" ".join(rotated))
        return variants

    def _majority_reasoning(self, responses: Sequence[str]) -> str:
        """Selecciona la respuesta con mayor respaldo interno."""

        def normalize(text: str) -> str:
            tokens = sorted(token.lower() for token in text.split())
            return " ".join(tokens)

        normalized = Counter(normalize(resp) for resp in responses)
        top_norm, _ = normalized.most_common(1)[0]
        for resp in responses:
            if normalize(resp) == top_norm:
                return resp
        return responses[0]

    def _calculate_divergence(self, responses: Sequence[str]) -> float:
        """Calcula el índice promedio de divergencia entre respuestas."""

        if len(responses) < 2:
            return 0.0
        divergences: list[float] = []
        token_sets = [set(resp.lower().split()) for resp in responses]
        for idx, left in enumerate(token_sets[:-1]):
            for right in token_sets[idx + 1 :]:
                union = left | right
                if not union:
                    divergences.append(0.0)
                    continue
                intersection = left & right
                distance = 1.0 - (len(intersection) / len(union))
                divergences.append(distance)
        if not divergences:
            return 0.0
        return round(sum(divergences) / len(divergences), 3)

    def _consistency_score(self, registros: Sequence[Ledger]) -> float:
        """Calcula una puntuación de consistencia basada en el ledger."""

        by_query: dict[str, list[str]] = {}
        for registro in registros:
            by_query.setdefault(registro.query, []).append(registro.response)
        inconsistencias = 0
        comparaciones = 0
        for responses in by_query.values():
            if len(responses) < 2:
                continue
            for idx, left in enumerate(responses[:-1]):
                for right in responses[idx + 1 :]:
                    comparaciones += 1
                    divergence = self._calculate_divergence([left, right])
                    if divergence > 0.2:
                        inconsistencias += 1
        if comparaciones == 0:
            return 1.0
        score = 1.0 - (inconsistencias / comparaciones)
        return max(0.0, round(score, 3))

    def _append_log(self, entry: Mapping[str, Any]) -> None:
        """Añade una entrada al registro cognitivo garantizando tamaño máximo."""

        with self._lock:
            data = self._read_log()
            data.append(dict(entry))
            data = data[-self._max_log_entries :]
            self.log_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )

    def _read_log(self) -> list[dict[str, object]]:
        try:
            payload = json.loads(self.log_path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                return list(payload)
        except json.JSONDecodeError:
            pass
        return []

    def _default_ledger_provider(self, limit: int) -> Sequence[Ledger]:
        statement = select(Ledger).order_by(desc(Ledger.id)).limit(max(limit, 1))
        with get_session() as session:
            registros = session.execute(statement).scalars().all()
        return list(reversed(registros))

    def _record_divergence(self, divergence: float) -> None:
        from horizonte.core import telemetry

        telemetry.record_cognitive_divergence(divergence)

    def _record_cycle(self, consistency: float) -> None:
        from horizonte.core import telemetry

        telemetry.record_cognitive_cycle(consistency)

    def _record_collective(self, score: float | None) -> None:
        from horizonte.core import telemetry

        telemetry.update_collective_consistency(score)


_MIRROR: CognitiveMirror | None = None


def get_cognitive_mirror() -> CognitiveMirror:
    """Devuelve la instancia global del espejo cognitivo."""

    global _MIRROR
    if _MIRROR is None:
        _MIRROR = CognitiveMirror()
    return _MIRROR


def set_cognitive_mirror(mirror: CognitiveMirror | None) -> None:
    """Permite reemplazar la instancia global (principalmente en pruebas)."""

    global _MIRROR
    _MIRROR = mirror


__all__ = [
    "CognitiveMirror",
    "CognitiveSnapshot",
    "get_cognitive_mirror",
    "set_cognitive_mirror",
]
