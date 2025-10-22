"""Mecanismos de aprendizaje adaptativo para el filtro ético de Horizonte."""

from __future__ import annotations

import json
from collections import Counter, deque
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Deque, Dict, List

_CACHE_FILENAME = "adaptive_cache.json"
_DEFAULT_CACHE_PATH = Path(__file__).resolve().parent / _CACHE_FILENAME


@dataclass(slots=True)
class InferenceRecord:
    """Representa una inferencia evaluada por el filtro ético."""

    timestamp: str
    query: str
    response_hash: str
    flags: List[str]
    response_time_ms: float
    allowed: bool

    @classmethod
    def from_payload(
        cls,
        query: str,
        response_hash: str,
        flags: Sequence[str],
        response_time_ms: float,
        allowed: bool,
    ) -> InferenceRecord:
        return cls(
            timestamp=datetime.now(timezone.utc).isoformat(),
            query=query,
            response_hash=response_hash,
            flags=list(flags),
            response_time_ms=float(response_time_ms),
            allowed=bool(allowed),
        )


@dataclass(slots=True)
class AdaptiveMetrics:
    """Agrupa las métricas calculadas por el entrenador adaptativo."""

    precision: float = 1.0
    consistency: float = 1.0
    bias_index: float = 0.0
    last_update: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, float | str]:
        return {
            "precision": self.precision,
            "consistency": self.consistency,
            "bias_index": self.bias_index,
            "last_update": self.last_update,
        }


class AdaptiveTrainer:
    """Motor de aprendizaje adaptativo para el filtro ético."""

    def __init__(
        self,
        cache_path: Path | None = None,
        buffer_size: int = 500,
    ) -> None:
        self.cache_path = cache_path or _DEFAULT_CACHE_PATH
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.buffer_size = buffer_size
        self._lock = Lock()
        self._buffer: Deque[InferenceRecord] = deque(maxlen=buffer_size)
        self._flag_history: Deque[str] = deque(maxlen=50)
        self._metrics = AdaptiveMetrics()
        self._sensitivity: Dict[str, float] = {
            "contenido_peligroso": 1.0,
            "posible_sesgo": 1.0,
        }
        self._load_cache()

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------
    def _load_cache(self) -> None:
        if not self.cache_path.exists():
            return
        try:
            payload = json.loads(self.cache_path.read_text())
        except json.JSONDecodeError:
            return
        registros = payload.get("buffer", [])
        for raw in registros[-self.buffer_size :]:
            try:
                record = InferenceRecord(
                    timestamp=raw["timestamp"],
                    query=raw["query"],
                    response_hash=raw["response_hash"],
                    flags=list(raw.get("flags", [])),
                    response_time_ms=float(raw.get("response_time_ms", 0.0)),
                    allowed=bool(raw.get("allowed", True)),
                )
            except KeyError:
                continue
            self._buffer.append(record)
        metrics = payload.get("metrics")
        if isinstance(metrics, dict):
            self._metrics = AdaptiveMetrics(
                precision=float(metrics.get("precision", 1.0)),
                consistency=float(metrics.get("consistency", 1.0)),
                bias_index=float(metrics.get("bias_index", 0.0)),
                last_update=str(
                    metrics.get(
                        "last_update",
                        datetime.now(timezone.utc).isoformat(),
                    )
                ),
            )
        sensitivity = payload.get("sensitivity")
        if isinstance(sensitivity, dict):
            for flag, value in sensitivity.items():
                try:
                    self._sensitivity[flag] = float(value)
                except (TypeError, ValueError):
                    continue

    def _persist(self) -> None:
        data = {
            "buffer": [asdict(record) for record in self._buffer],
            "metrics": self._metrics.to_dict(),
            "sensitivity": self._sensitivity,
        }
        self.cache_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    # ------------------------------------------------------------------
    # Registro y métricas
    # ------------------------------------------------------------------
    def log_inference(
        self,
        query: str,
        response_hash: str,
        flags: Sequence[str],
        response_time_ms: float,
        allowed: bool,
    ) -> None:
        """Registra una inferencia en el buffer y recalcula métricas."""

        record = InferenceRecord.from_payload(
            query=query,
            response_hash=response_hash,
            flags=flags,
            response_time_ms=response_time_ms,
            allowed=allowed,
        )
        with self._lock:
            self._buffer.append(record)
            self._recompute_metrics()
            self._persist()
        try:
            from horizonte.core.metacognition import record_cognitive_event

            record_cognitive_event(
                "adaptive_learning",
                "log_inference",
                {
                    "flags": list(flags),
                    "allowed": bool(allowed),
                    "response_time_ms": float(response_time_ms),
                },
            )
        except Exception:  # pragma: no cover - la metacognición no debe fallar
            pass

    def _recompute_metrics(self) -> None:
        total = len(self._buffer)
        if total == 0:
            self._metrics = AdaptiveMetrics()
            return

        allowed_count = sum(1 for record in self._buffer if record.allowed)
        precision = allowed_count / total

        bias_events = sum(1 for record in self._buffer if "posible_sesgo" in record.flags)
        bias_index = bias_events / total

        consistency = self._calculate_consistency()
        self._metrics = AdaptiveMetrics(
            precision=round(precision, 3),
            consistency=round(consistency, 3),
            bias_index=round(bias_index, 3),
            last_update=datetime.now(timezone.utc).isoformat(),
        )

    def _calculate_consistency(self) -> float:
        if not self._buffer:
            return 1.0
        history: Dict[str, set[tuple[bool, tuple[str, ...]]]] = {}
        inconsistencies = 0
        for record in self._buffer:
            key = record.response_hash
            state = (record.allowed, tuple(sorted(record.flags)))
            seen = history.setdefault(key, set())
            if seen and state not in seen:
                inconsistencies += 1
            seen.add(state)
        total = len(self._buffer)
        consistency = 1.0 - (inconsistencies / total)
        return max(0.0, min(1.0, consistency))

    # ------------------------------------------------------------------
    # Ajuste adaptativo
    # ------------------------------------------------------------------
    def update_model_feedback(self, flags: Sequence[str] | None = None) -> Dict[str, float]:
        """Ajusta la sensibilidad del filtro según los patrones de flags."""

        with self._lock:
            if flags:
                self._flag_history.extend(flags)
            counts = Counter(self._flag_history)
            adjustments: Dict[str, float] = {}
            for flag, count in counts.items():
                if count >= 3:
                    current = self._sensitivity.get(flag, 1.0)
                    increment = 0.1 * (count // 3)
                    nuevo_valor = min(3.0, round(current + increment, 3))
                    if nuevo_valor != current:
                        self._sensitivity[flag] = nuevo_valor
                        adjustments[flag] = nuevo_valor
            # reducción gradual hacia el valor base cuando no hay recurrencia
            for flag, current in list(self._sensitivity.items()):
                if counts.get(flag, 0) == 0 and current > 1.0:
                    nuevo_valor = max(1.0, round(current - 0.05, 3))
                    if nuevo_valor != current:
                        self._sensitivity[flag] = nuevo_valor
                        adjustments[flag] = nuevo_valor
            if adjustments:
                self._persist()
            try:
                from horizonte.core.metacognition import record_cognitive_event

                record_cognitive_event(
                    "adaptive_learning",
                    "update_model_feedback",
                    {
                        "flags": list(flags or []),
                        "ajustes": dict(adjustments),
                    },
                )
            except Exception:  # pragma: no cover
                pass
            return dict(self._sensitivity)

    def export_metrics(self) -> Dict[str, float | str | Dict[str, float]]:
        """Devuelve un resumen serializable de las métricas actuales."""

        with self._lock:
            payload: Dict[str, float | str | Dict[str, float]] = {
                **self._metrics.to_dict(),
                "sensitivity": dict(self._sensitivity),
            }
        return payload

    # ------------------------------------------------------------------
    # Utilidades públicas
    # ------------------------------------------------------------------
    def reset_buffer(self) -> None:
        """Reinicia el buffer de inferencias y restaura métricas base."""

        with self._lock:
            self._buffer = deque(maxlen=self.buffer_size)
            self._flag_history.clear()
            self._metrics = AdaptiveMetrics()
            self._sensitivity = {
                "contenido_peligroso": 1.0,
                "posible_sesgo": 1.0,
            }
            self._persist()

    @property
    def buffer(self) -> List[InferenceRecord]:
        """Devuelve una copia inmutable del buffer actual."""

        with self._lock:
            return list(self._buffer)


_GLOBAL_TRAINER: AdaptiveTrainer | None = None


def get_adaptive_trainer() -> AdaptiveTrainer:
    """Obtiene el entrenador adaptativo global."""

    global _GLOBAL_TRAINER
    if _GLOBAL_TRAINER is None:
        _GLOBAL_TRAINER = AdaptiveTrainer()
    return _GLOBAL_TRAINER


def set_adaptive_trainer(trainer: AdaptiveTrainer | None) -> None:
    """Permite reemplazar el entrenador global (principalmente para pruebas)."""

    global _GLOBAL_TRAINER
    _GLOBAL_TRAINER = trainer
