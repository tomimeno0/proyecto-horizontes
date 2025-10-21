"""Visualizador simple de conjuntos de datos educativos."""

from __future__ import annotations

from typing import Iterable, List


def listar_campos(dataset: Iterable[dict]) -> List[str]:
    """Retorna los campos disponibles en un conjunto de datos iterable."""
    campos: set[str] = set()
    for fila in dataset:
        campos.update(fila.keys())
    return sorted(campos)


if __name__ == "__main__":  # pragma: no cover - ejemplo manual
    datos = [{"tema": "ética", "nivel": "básico"}, {"tema": "técnica", "nivel": "avanzado", "duracion": 40}]
    print(listar_campos(datos))
