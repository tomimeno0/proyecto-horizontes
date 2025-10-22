"""Sistema básico de gobernanza con propuestas y votos."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Dict, List, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class Proposal(BaseModel):
    """Propuesta registrada en el sistema in-memory."""

    id: str
    title: str = Field(..., min_length=3)
    description: str = Field(..., min_length=10)
    votes_for: int = 0
    votes_against: int = 0
    created_at: datetime


VoteValue = Literal["for", "against"]


class VoteSystem:
    """Gestor concurrente de propuestas y recuentos."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._proposals: Dict[str, Proposal] = {}

    def create_proposal(self, title: str, description: str) -> Proposal:
        with self._lock:
            proposal_id = uuid4().hex
            proposal = Proposal(
                id=proposal_id,
                title=title,
                description=description,
                created_at=datetime.now(timezone.utc),
            )
            self._proposals[proposal_id] = proposal
            return proposal

    def vote(self, proposal_id: str, value: VoteValue) -> Proposal:
        with self._lock:
            proposal = self._proposals.get(proposal_id)
            if proposal is None:
                raise ValueError("La propuesta no existe.")
            data = proposal.model_dump()
            if value == "for":
                data["votes_for"] = proposal.votes_for + 1
            else:
                data["votes_against"] = proposal.votes_against + 1
            updated = Proposal(**data)
            self._proposals[proposal_id] = updated
            return updated

    def get_results(self) -> List[Proposal]:
        with self._lock:
            return list(self._proposals.values())

    def get_proposal(self, proposal_id: str) -> Proposal:
        with self._lock:
            proposal = self._proposals.get(proposal_id)
            if proposal is None:
                raise ValueError("La propuesta no existe.")
            return proposal

    def reset(self) -> None:
        with self._lock:
            self._proposals.clear()


_SYSTEM = VoteSystem()


def create_proposal(title: str, description: str) -> Proposal:
    return _SYSTEM.create_proposal(title, description)


def vote(proposal_id: str, value: VoteValue) -> Proposal:
    return _SYSTEM.vote(proposal_id, value)


def get_results() -> List[Proposal]:
    return _SYSTEM.get_results()


def get_proposal(proposal_id: str) -> Proposal:
    return _SYSTEM.get_proposal(proposal_id)


def reset_system() -> None:
    _SYSTEM.reset()


__all__ = [
    "Proposal",
    "VoteSystem",
    "create_proposal",
    "get_proposal",
    "get_results",
    "reset_system",
    "vote",
]
