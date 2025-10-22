"""Filtro ético básico para las respuestas del sistema."""

from __future__ import annotations

from typing import Dict, List, Sequence

from .adaptive_learning import AdaptiveTrainer, get_adaptive_trainer, set_adaptive_trainer

PELIGROSAS = {"violencia", "odio", "armas", "ataque"}
SESGO = {"raza", "género", "religión"}

ADAPTIVE_TRAINER = get_adaptive_trainer()


def check(response: str) -> Dict[str, object]:
    """Evalúa de forma simple si la respuesta puede ser problemática."""

    texto = response.lower()
    flags: List[str] = []

    if any(palabra in texto for palabra in PELIGROSAS):
        flags.append("contenido_peligroso")
    if any(palabra in texto for palabra in SESGO):
        flags.append("posible_sesgo")

    permitido = not flags
    notas = (
        "Respuesta considerada segura."
        if permitido
        else "Se detectaron indicadores a revisar."
    )
    if flags:
        ADAPTIVE_TRAINER.update_model_feedback(flags)
    return {
        "allowed": permitido,
        "flags": flags,
        "notes": notas,
    }


def register_adaptive_inference(
    *,
    query: str,
    response_hash: str,
    flags: Sequence[str],
    response_time_ms: float,
    allowed: bool,
) -> Dict[str, object]:
    """Registra la inferencia en el entrenador adaptativo y retorna métricas."""

    ADAPTIVE_TRAINER.log_inference(
        query=query,
        response_hash=response_hash,
        flags=flags,
        response_time_ms=response_time_ms,
        allowed=allowed,
    )
    return ADAPTIVE_TRAINER.export_metrics()


def get_adaptive_metrics() -> Dict[str, object]:
    """Obtiene las métricas adaptativas actuales."""

    return ADAPTIVE_TRAINER.export_metrics()


def set_adaptive_trainer_override(trainer: AdaptiveTrainer | None) -> None:
    """Permite reemplazar el entrenador global (uso en pruebas)."""

    global ADAPTIVE_TRAINER
    set_adaptive_trainer(trainer)
    ADAPTIVE_TRAINER = get_adaptive_trainer()
