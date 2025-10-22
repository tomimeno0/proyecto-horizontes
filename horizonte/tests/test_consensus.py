"""Pruebas unitarias para el gestor de consenso."""

from __future__ import annotations

import pytest

from net import consensus_manager
from net.node_registry import NodePayload, get_registry


@pytest.fixture(autouse=True)
def limpiar_registro() -> None:
    """Limpia el registro global antes de cada prueba."""

    get_registry().clear()


def _registrar_nodos(total: int, aprobaciones: dict[int, bool]) -> dict[str, bool]:
    """Registra nodos y devuelve un mapa dirección→resultado esperado."""

    address_map: dict[str, bool] = {}
    registry = get_registry()
    for idx in range(1, total + 1):
        node_id = f"validator-{idx}"
        address = f"http://validator{idx}.example.com"
        registry.register(NodePayload(node_id=node_id, address=address, status="activo"))
        address_map[address] = aprobaciones.get(idx, False)
    return address_map


def test_broadcast_result_aprueba_dos_tercios(monkeypatch: pytest.MonkeyPatch) -> None:
    """Debe aprobar cuando al menos 2/3 de los nodos validan el hash."""

    respuestas = _registrar_nodos(5, {1: True, 2: True, 3: True, 4: True})

    def _falso_verificador(address: str, payload: dict[str, str]) -> bool:
        return respuestas[address]

    monkeypatch.setattr(consensus_manager, "_simulate_remote_verification", _falso_verificador)

    resultado = consensus_manager.broadcast_result("origin-node", "hash-prueba")
    assert resultado["approved"] is True
    assert len(resultado["validators"]) == 4


def test_broadcast_result_falla_sin_quorum(monkeypatch: pytest.MonkeyPatch) -> None:
    """Debe rechazar cuando no se alcanza el umbral mínimo requerido."""

    respuestas = _registrar_nodos(5, {1: True, 2: True, 3: True})

    def _falso_verificador(address: str, payload: dict[str, str]) -> bool:
        return respuestas[address]

    monkeypatch.setattr(consensus_manager, "_simulate_remote_verification", _falso_verificador)

    resultado = consensus_manager.broadcast_result("origin-node", "hash-prueba")
    assert resultado["approved"] is False
    assert set(resultado["validators"]) == {"validator-1", "validator-2", "validator-3"}
