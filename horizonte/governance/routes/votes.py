"""Rutas de FastAPI para la gobernanza colaborativa."""

from __future__ import annotations

from typing import List, Literal

from fastapi import APIRouter, HTTPException, status
from horizonte.governance import vote_system
from horizonte.governance.vote_system import Proposal
from pydantic import BaseModel, Field

router = APIRouter(tags=["governance"])


class ProposalPayload(BaseModel):
    title: str = Field(..., min_length=3)
    description: str = Field(..., min_length=10)


class VotePayload(BaseModel):
    value: Literal["for", "against"]


class ProposalResult(BaseModel):
    proposal: Proposal
    total_votes: int
    approved: bool


@router.post("/proposals", response_model=Proposal, status_code=status.HTTP_201_CREATED)
def create_proposal(payload: ProposalPayload) -> Proposal:
    """Crea una nueva propuesta disponible para votar."""

    return vote_system.create_proposal(payload.title, payload.description)


@router.get("/proposals", response_model=List[Proposal])
def list_proposals() -> List[Proposal]:
    """Devuelve todas las propuestas registradas."""

    return vote_system.get_results()


@router.post("/proposals/{proposal_id}/vote", response_model=Proposal)
def cast_vote(proposal_id: str, payload: VotePayload) -> Proposal:
    """Registra un voto a favor o en contra."""

    try:
        return vote_system.vote(proposal_id, payload.value)
    except ValueError as exc:  # pragma: no cover - validación HTTP
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/proposals/{proposal_id}/results", response_model=ProposalResult)
def proposal_results(proposal_id: str) -> ProposalResult:
    """Entrega los resultados agregados de una propuesta."""

    try:
        proposal = vote_system.get_proposal(proposal_id)
    except ValueError as exc:  # pragma: no cover - validación HTTP
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    total = proposal.votes_for + proposal.votes_against
    approved = proposal.votes_for > proposal.votes_against
    return ProposalResult(proposal=proposal, total_votes=total, approved=approved)


__all__ = ["router"]
