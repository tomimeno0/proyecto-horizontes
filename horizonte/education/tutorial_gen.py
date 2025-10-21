"""Generador básico de tutoriales educativos."""

from __future__ import annotations

from typing import Dict, List


def generar_tutorial(tema: str, pasos: List[str]) -> Dict[str, object]:
    """Crea una estructura de tutorial con metadatos mínimos."""
    return {
        "tema": tema,
        "pasos": pasos,
        "nivel": "intermedio",
        "duracion_estimada_min": 25,
    }


if __name__ == "__main__":  # pragma: no cover - ejemplo manual
    ejemplo = generar_tutorial("Uso responsable de IA", ["Introducción", "Principios éticos", "Evaluación"])
    print(ejemplo)
