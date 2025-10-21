"""Protocolo de sincronización entre nodos Horizonte."""

from __future__ import annotations

from typing import Dict, List


class SyncProtocol:
    """Stub del protocolo de sincronización basado en gRPC."""

    def propose_sync(self, hashes: List[str]) -> Dict[str, object]:
        """Simula el intercambio de hashes entre nodos.

        En una futura iteración se definirá un archivo `.proto` para implementar el
        canal gRPC que coordine la replicación del ledger entre nodos Horizonte.
        """

        return {
            "received": len(hashes),
            "unique": len(set(hashes)),
            "status": "aceptado" if hashes else "sin_datos",
        }
