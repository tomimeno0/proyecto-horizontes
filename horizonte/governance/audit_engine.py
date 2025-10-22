"""Motor de auditoría y generación de reportes verificables."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from governance.dashboard.main import metrics_manager
from horizonte.common.db import Ledger, get_session
from horizonte.common.security import hash_text_sha256
from horizonte.core.metacognition import get_cognitive_mirror
from horizonte.core.security_monitor import get_security_monitor
from horizonte.core.telemetry import get_metrics
from horizonte.core.trace_logger import serialize_record
from horizonte.net.consensus_manager import get_consensus_manager
from horizonte.net.node_registry import get_registry

AUDIT_REPORT_PATH = Path(__file__).with_name("audit_report.json")


def _ledger_snapshot(limit: int = 20) -> list[dict[str, Any]]:
    """Obtiene las últimas inferencias registradas en el ledger."""

    statement = select(Ledger).order_by(Ledger.id.desc()).limit(max(limit, 1))
    with get_session() as session:
        registros: Iterable[Ledger] = session.execute(statement).scalars().all()
    return [serialize_record(registro) for registro in registros]


def _network_snapshot() -> dict[str, Any]:
    """Construye un resumen verificable del estado de la red."""

    registry = get_registry()
    nodes = []
    for node in registry.list_nodes():
        nodes.append(
            {
                "node_id": node.node_id,
                "status": node.status,
                "last_activity": (node.last_activity.isoformat() if node.last_activity else None),
                "avg_latency_ms": node.avg_latency_ms,
                "sync_score": node.sync_score,
            }
        )
    sync_values = [n["sync_score"] for n in nodes if n["sync_score"] is not None]
    network_digest = hash_text_sha256(json.dumps(nodes, sort_keys=True, default=str))
    return {
        "nodes": nodes,
        "average_sync": (round(sum(sync_values) / len(sync_values), 3) if sync_values else 0.0),
        "digest": network_digest,
    }


def _consensus_snapshot() -> dict[str, Any]:
    """Incluye los últimos resultados del gestor de consenso."""

    manager = get_consensus_manager()
    history = getattr(manager, "_history", [])
    recent = history[-5:] if history else []
    return {
        "mode": manager.mode,
        "failure_streak": manager.failure_streak,
        "recent_history": recent,
    }


def audit_snapshot(limit_inferencias: int = 20) -> dict[str, Any]:
    """Genera un snapshot auditable y lo exporta con firma SHA256."""

    timestamp = datetime.now(timezone.utc).isoformat()
    inferences = _ledger_snapshot(limit_inferencias)
    metrics = get_metrics()
    cognition = asdict(get_cognitive_mirror().status())
    consensus = metrics_manager.snapshot()
    network = _network_snapshot()
    consensus_state = _consensus_snapshot()
    security_monitor = get_security_monitor()
    security_state = security_monitor.check_integrity(record_alert=False)

    snapshot = {
        "timestamp": timestamp,
        "inferences": inferences,
        "metrics": {
            "telemetry": metrics,
            "cognitive": {
                "divergence_index": cognition["divergence_index"],
                "global_consistency": cognition["global_consistency"],
                "collective_consistency": cognition["collective_consistency"],
                "cycles": cognition["cycles"],
                "last_audit": cognition["last_audit"],
            },
            "dashboard": consensus,
            "network": network,
        },
        "consensus": consensus_state,
        "security": security_state,
    }

    payload = {
        "generated_at": timestamp,
        "snapshot": snapshot,
    }
    signature_source = json.dumps(snapshot, sort_keys=True, ensure_ascii=False, default=str)
    signature = hash_text_sha256(signature_source)
    payload["signature"] = signature

    AUDIT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_REPORT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    return payload


__all__ = ["audit_snapshot", "AUDIT_REPORT_PATH"]
