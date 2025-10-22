"""Pruebas para el registro dinámico de nodos."""

from __future__ import annotations

from fastapi.testclient import TestClient

from horizonte.api.main import app
from horizonte.net.node_registry import get_registry


def setup_function() -> None:  # pragma: no cover - usado por pytest
    get_registry().clear()


def test_register_list_and_delete_nodes() -> None:
    registry = get_registry()
    with TestClient(app) as client:
        payload = {"node_id": "node-a", "address": "http://node-a.test"}
        response = client.post("/nodes/register", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "active"

        payload_b = {"node_id": "node-b", "address": "http://node-b.test"}
        response_b = client.post("/nodes/register", json=payload_b)
        assert response_b.status_code == 201

        list_response = client.get("/nodes")
        assert list_response.status_code == 200
        nodes = list_response.json()
        assert len(nodes) == 2

        delete_response = client.delete("/nodes/node-a")
        assert delete_response.status_code == 204

        assert registry.get("node-a") is None
        assert len(registry.list_nodes()) == 1


def test_register_rejects_duplicate_address() -> None:
    with TestClient(app) as client:
        payload = {"node_id": "node-a", "address": "http://duplicate.test"}
        assert client.post("/nodes/register", json=payload).status_code == 201

        payload_dup = {"node_id": "node-b", "address": "http://duplicate.test"}
        response = client.post("/nodes/register", json=payload_dup)
        assert response.status_code == 400
