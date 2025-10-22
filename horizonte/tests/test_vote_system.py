"""Pruebas del sistema básico de votaciones."""

from __future__ import annotations

from horizonte.governance import vote_system


def setup_function() -> None:  # pragma: no cover - usado por pytest
    vote_system.reset_system()


def test_create_and_vote_proposal() -> None:
    proposal = vote_system.create_proposal(
        "Nodo comunitario", "Financiar un nuevo nodo de validación en LatAm."
    )
    assert proposal.votes_for == 0
    assert proposal.votes_against == 0

    updated = vote_system.vote(proposal.id, "for")
    assert updated.votes_for == 1

    updated = vote_system.vote(proposal.id, "against")
    assert updated.votes_against == 1

    proposals = vote_system.get_results()
    assert len(proposals) == 1
    summary = vote_system.get_proposal(proposal.id)
    assert summary.votes_for == 1
    assert summary.votes_against == 1
