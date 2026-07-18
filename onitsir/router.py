"""The Router — matches a mission goal to the right specialists.

The Roster gives us the *who*. The Router is the dispatch layer
that turns a free-text goal into a ranked crew, so a mission is always staffed by
the most relevant experts rather than a generic assistant.
"""
from __future__ import annotations

from dataclasses import dataclass

from .roster import Roster, Specialist


@dataclass(frozen=True)
class Assignment:
    """A specialist assigned to a mission, with the confidence of the match."""
    specialist: Specialist
    score: int

    @property
    def confidence(self) -> str:
        if self.score >= 8:
            return "high"
        if self.score >= 4:
            return "medium"
        return "low"


class Router:
    def __init__(self, roster: Roster):
        self._roster = roster

    def route(self, goal: str, crew_size: int = 3) -> list[Assignment]:
        """Pick the top `crew_size` specialists for a goal.

        Raises ValueError on an empty goal. Never fabricates a match: if nothing
        scores, returns an empty crew and lets the caller decide (the Engine
        surfaces this as a real "no confident match" state, not a silent guess).
        """
        if not goal or not goal.strip():
            raise ValueError("Cannot route an empty goal.")
        if crew_size < 1:
            raise ValueError("crew_size must be >= 1")
        matches = self._roster.search(goal, limit=crew_size)
        return [Assignment(specialist=s, score=sc) for s, sc in matches]
