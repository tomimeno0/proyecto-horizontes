"""Filtro ético básico para las respuestas del sistema."""

from __future__ import annotations

from typing import Dict, List


PELIGROSAS = {"violencia", "odio", "armas", "ataque"}
SESGO = {"raza", "género", "religión"}


def check(response: str) -> Dict[str, object]:
    """Evalúa de forma simple si la respuesta puede ser problemática."""
    texto = response.lower()
    flags: List[str] = []

    if any(palabra in texto for palabra in PELIGROSAS):
        flags.append("contenido_peligroso")
    if any(palabra in texto for palabra in SESGO):
        flags.append("posible_sesgo")

    permitido = not flags
    notas = "Respuesta considerada segura." if permitido else "Se detectaron indicadores a revisar."
    return {
        "allowed": permitido,
        "flags": flags,
        "notes": notas,
    }
