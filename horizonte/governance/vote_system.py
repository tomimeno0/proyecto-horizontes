"""Sistema de votación in-memory para experimentar con gobernanza."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, cast

from pydantic import BaseModel, Field, ValidationError


class Proposal(BaseModel):
    """Propuesta registrada en el sistema."""

    id: str = Field(..., min_length=3)
    title: str = Field(..., min_length=5)
    description: str = Field(..., min_length=10)


class Vote(BaseModel):
    """Voto emitido por una persona participante."""

    proposal_id: str
    voter_id: str
    value: bool


@dataclass
class VoteRegistry:
    """Registro simple de propuestas y votos en memoria."""

    proposals: dict[str, Proposal] = field(default_factory=dict)
    votes: dict[str, list[Vote]] = field(default_factory=dict)

    def register_proposal(self, data: Mapping[str, object]) -> Proposal:
        """Registra una nueva propuesta validando los datos."""
        payload = cast(Mapping[str, Any], data)
        try:
            proposal = Proposal(**payload)
        except ValidationError as exc:
            raise ValueError(f"Propuesta inválida: {exc}") from exc
        self.proposals[proposal.id] = proposal
        self.votes.setdefault(proposal.id, [])
        return proposal

    def cast_vote(self, data: Mapping[str, object]) -> Vote:
        """Registra un voto válido para una propuesta existente."""
        payload = cast(Mapping[str, Any], data)
        try:
            vote = Vote(**payload)
        except ValidationError as exc:
            raise ValueError(f"Voto inválido: {exc}") from exc
        if vote.proposal_id not in self.proposals:
            raise ValueError("La propuesta no existe.")
        votos = self.votes.setdefault(vote.proposal_id, [])
        if any(v.voter_id == vote.voter_id for v in votos):
            raise ValueError("La persona ya votó esta propuesta.")
        votos.append(vote)
        return vote

    def tally(self, proposal_id: str) -> dict[str, object]:
        """Calcula resultados simples para una propuesta."""
        if proposal_id not in self.proposals:
            raise ValueError("La propuesta no existe.")
        votos = self.votes.get(proposal_id, [])
        total = len(votos)
        favor = sum(1 for v in votos if v.value)
        return {
            "proposal": self.proposals[proposal_id].model_dump(),
            "total_votes": total,
            "approved": favor,
            "rejected": total - favor,
        }
