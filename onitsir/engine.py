"""The Engine — where the three systems fuse into one product.

Engine.run(goal) executes a full ONITSIR mission:

  1. ROUTE   — the Router staffs a crew from the Roster (agency-agents).
  2. WORKFLOW — a Workflow drives the mission through phases (gsd-pro),
  3. VERIFY   — each phase closes only on Iron-Law evidence (superpowers).

The Engine takes a `verifier` callable: given a Phase, it returns Evidence.
In production that runs real commands/tests; in tests it's injected. This keeps
the Engine honest — it can never mark a phase done without asking the verifier
for proof, and the gate independently validates that proof.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .roster import Roster
from .router import Assignment, Router
from .verification import Evidence, VerificationError, VerificationGate
from .workflow import Phase, Workflow

Verifier = Callable[[Phase], Evidence]


@dataclass
class Mission:
    goal: str
    crew: list[Assignment] = field(default_factory=list)
    phase_log: list[str] = field(default_factory=list)
    shipped: bool = False
    blocked_reason: str | None = None

    @property
    def crew_names(self) -> list[str]:
        return [a.specialist.name for a in self.crew]


class Engine:
    def __init__(
        self,
        roster: Roster | None = None,
        gate: VerificationGate | None = None,
        crew_size: int = 3,
    ):
        self._roster = roster or Roster.load()
        self._router = Router(self._roster)
        self._gate = gate or VerificationGate()
        self._crew_size = crew_size

    def run(self, goal: str, verifier: Verifier) -> Mission:
        """Run a full mission. Never claims 'shipped' without passing every gate.

        If the verifier ever returns evidence that fails the Iron Law, the mission
        stops at that phase with `blocked_reason` set and `shipped=False` — an
        honest failure, not a fake success.
        """
        mission = Mission(goal=goal)
        mission.crew = self._router.route(goal, crew_size=self._crew_size)

        workflow = Workflow(gate=self._gate)
        # Drive every phase to completion, each gated by fresh evidence.
        while not workflow.shipped:
            phase = workflow.current
            evidence = verifier(phase)
            try:
                workflow.complete_current(evidence)
                mission.phase_log.append(f"{phase.value}: verified")
            except VerificationError as e:
                mission.blocked_reason = f"{phase.value}: {e}"
                mission.phase_log.append(f"{phase.value}: BLOCKED — {e}")
                mission.shipped = False
                return mission

        mission.shipped = True
        return mission

    def preview_crew(self, goal: str) -> list[Assignment]:
        """Route only — show who would be staffed, no execution."""
        return self._router.route(goal, crew_size=self._crew_size)
