"""Servicio verificador simulado para Horizonte."""

from __future__ import annotations

from typing import Dict, List

import uvicorn
from fastapi import FastAPI


def quorum_validate(hashes: List[str]) -> Dict[str, object]:
    """Evalúa si existe quórum de 2/3 para los hashes proporcionados."""
    total = len(hashes)
    if total == 0:
        return {"quorum": False, "total": 0, "unique": 0}
    unique = len(set(hashes))
    quorum = unique / total >= (2 / 3)
    return {"quorum": quorum, "total": total, "unique": unique}


def create_app() -> FastAPI:
    """Crea una aplicación FastAPI ligera para el verificador."""
    app = FastAPI(title="Horizonte Verifier")

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/quorum")
    async def quorum_endpoint(payload: Dict[str, List[str]]) -> Dict[str, object]:
        hashes = payload.get("hashes", [])
        return quorum_validate(hashes)

    return app


if __name__ == "__main__":  # pragma: no cover - punto de entrada CLI
    uvicorn.run(create_app(), host="0.0.0.0", port=8080)
