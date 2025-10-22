"""Microservicio verificador para el consenso simulado de Horizonte."""

from __future__ import annotations

import asyncio
from random import random
from typing import Dict

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn


class VerifyRequest(BaseModel):
    """Estructura esperada para las solicitudes de verificación."""

    hash: str


class VerifyResponse(BaseModel):
    """Resultado estandarizado del verificador distribuido."""

    valid: bool


app = FastAPI(title="Horizonte Verifier", docs_url=None, redoc_url=None)


async def _heartbeat() -> None:
    """Mantiene vivo al servicio y permite enganchar métricas futuras."""

    while True:
        await asyncio.sleep(60)


@app.on_event("startup")
async def _startup() -> None:
    app.state._background = asyncio.create_task(_heartbeat())


@app.on_event("shutdown")
async def _shutdown() -> None:
    background = getattr(app.state, "_background", None)
    if background:
        background.cancel()


@app.get("/health")
async def health() -> Dict[str, str]:
    """Indica el estado de salud del servicio."""

    return {"status": "ok"}


@app.post("/verify", response_model=VerifyResponse)
async def verify(payload: VerifyRequest) -> VerifyResponse:
    """Responde aleatoriamente, aprobando aproximadamente 2/3 de las veces."""

    _ = payload.hash  # se reserva para futuras validaciones semánticas
    return VerifyResponse(valid=random() < (2 / 3))


if __name__ == "__main__":  # pragma: no cover - punto de entrada CLI
    uvicorn.run(app, host="0.0.0.0", port=8001)
