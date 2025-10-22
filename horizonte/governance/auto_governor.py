"""Gobernanza autónoma basada en métricas éticas globales."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Deque, Dict, List

import anyio

from horizonte.core.telemetry import get_metrics
from horizonte.net.node_manager import NodeManager
from horizonte.net.node_registry import NodeRegistry, get_registry
from horizonte.governance import vote_system


@dataclass
class GovernanceAction:
    """Representa una acción automática generada por el gobernador."""

    proposal_id: str
    reason: str
    created_at: datetime


class AutoGovernor:
    """Evalúa métricas y genera ajustes de forma autónoma."""

    def __init__(
        self,
        *,
        interval: float = 300.0,
        registry: NodeRegistry | None = None,
        node_manager: NodeManager | None = None,
    ) -> None:
        self.interval = interval
        self.registry = registry or get_registry()
        self.node_manager = node_manager or NodeManager()
        self._bias_history: Deque[float] = deque(maxlen=24)
        self._active_conditions: Dict[str, str] = {}
        self._running = False
        self.history: List[GovernanceAction] = []

    def _weighted_vote(self, favour: bool) -> float:
        nodes = self.registry.get_active_nodes()
        weight = sum(node.reliability for node in nodes) or 0.0
        if favour:
            return weight
        return 0.0

    def _resolve_proposal(self, proposal_id: str, favour: bool) -> None:
        weight_for = self._weighted_vote(favour)
        weight_against = 0.0 if favour else weight_for
        if favour:
            vote_system.add_votes(proposal_id, votes_for=weight_for)
        else:
            vote_system.add_votes(proposal_id, votes_against=weight_against)

    def _create_system_proposal(self, title: str, description: str) -> GovernanceAction:
        proposal = vote_system.create_proposal(
            title,
            description,
            tags=["system"],
            system=True,
        )
        self._resolve_proposal(proposal.id, favour=True)
        action = GovernanceAction(
            proposal_id=proposal.id,
            reason=description,
            created_at=datetime.now(timezone.utc),
        )
        self.history.append(action)
        return action

    async def evaluate_once(self) -> List[GovernanceAction]:
        metrics = get_metrics()
        ethics = metrics.get("ethics_adaptive", {})
        bias = float(ethics.get("bias_index", 0.0))
        precision = float(ethics.get("precision", 1.0))
        self._bias_history.append(bias)
        bias_average = sum(self._bias_history) / len(self._bias_history)

        actions: List[GovernanceAction] = []

        if bias_average > 0.3:
            if "bias" not in self._active_conditions:
                reason = (
                    f"Bias promedio {bias_average:.2f} excede límite 0.30. Se propone ajuste ético."
                )
                actions.append(
                    self._create_system_proposal(
                        "Ajuste ético automático",
                        reason,
                    )
                )
                self._active_conditions["bias"] = "active"
        else:
            self._active_conditions.pop("bias", None)

        if precision < 0.7:
            if "precision" not in self._active_conditions:
                reason = (
                    f"Precisión ética global {precision:.2f} por debajo de 0.70. Se inicia recalibración."
                )
                actions.append(
                    self._create_system_proposal(
                        "Recalibración ética automática",
                        reason,
                    )
                )
                self._active_conditions["precision"] = "active"
        else:
            self._active_conditions.pop("precision", None)

        return actions

    async def run(self) -> None:
        if self._running:
            return
        self._running = True
        try:
            while self._running:
                await self.evaluate_once()
                await anyio.sleep(self.interval)
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False


__all__ = ["AutoGovernor", "GovernanceAction"]

