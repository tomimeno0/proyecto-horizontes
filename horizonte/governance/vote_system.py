"""Sistema básico de gobernanza con propuestas y votos."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class Proposal(BaseModel):
    """Propuesta registrada en el sistema in-memory."""

    id: str
    title: str = Field(..., min_length=3)
    description: str = Field(..., min_length=10)
    votes_for: float = 0.0
    votes_against: float = 0.0
    created_at: datetime
    tags: List[str] = Field(default_factory=list)
    system: bool = False


VoteValue = Literal["for", "against"]


class VoteSystem:
    """Gestor concurrente de propuestas y recuentos."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._proposals: Dict[str, Proposal] = {}

    def create_proposal(
        self,
        title: str,
        description: str,
        *,
        tags: Optional[List[str]] = None,
        system: bool = False,
    ) -> Proposal:
        with self._lock:
            proposal_id = uuid4().hex
            proposal = Proposal(
                id=proposal_id,
                title=title,
                description=description,
                created_at=datetime.now(timezone.utc),
                tags=list(tags or []),
                system=system,
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
                data["votes_for"] = round(proposal.votes_for + 1, 3)
            else:
                data["votes_against"] = round(proposal.votes_against + 1, 3)
            updated = Proposal(**data)
            self._proposals[proposal_id] = updated
            return updated

    def add_votes(
        self, proposal_id: str, *, votes_for: float = 0.0, votes_against: float = 0.0
    ) -> Proposal:
        with self._lock:
            proposal = self._proposals.get(proposal_id)
            if proposal is None:
                raise ValueError("La propuesta no existe.")
            data = proposal.model_dump()
            if votes_for:
                data["votes_for"] = round(proposal.votes_for + votes_for, 3)
            if votes_against:
                data["votes_against"] = round(proposal.votes_against + votes_against, 3)
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


def create_proposal(
    title: str,
    description: str,
    *,
    tags: Optional[List[str]] = None,
    system: bool = False,
) -> Proposal:
    return _SYSTEM.create_proposal(title, description, tags=tags, system=system)


def vote(proposal_id: str, value: VoteValue) -> Proposal:
    return _SYSTEM.vote(proposal_id, value)


def get_results() -> List[Proposal]:
    return _SYSTEM.get_results()


def get_proposal(proposal_id: str) -> Proposal:
    return _SYSTEM.get_proposal(proposal_id)


def reset_system() -> None:
    _SYSTEM.reset()


def add_votes(
    proposal_id: str, *, votes_for: float = 0.0, votes_against: float = 0.0
) -> Proposal:
    return _SYSTEM.add_votes(
        proposal_id, votes_for=votes_for, votes_against=votes_against
    )


__all__ = [
    "Proposal",
    "VoteSystem",
    "create_proposal",
    "add_votes",
    "get_proposal",
    "get_results",
    "reset_system",
    "vote",
]

