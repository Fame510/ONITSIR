"""The Engine — where the systems fuse into one product.

Engine.run(goal) executes a full ONITSIR mission through four layers:

  1. ROUTE    — the Router staffs a crew from the Roster.
  2. GOVERN   — Shackle rules ALLOW / DENY / HITL on each phase BEFORE it runs
                (budget, loop, repeat breakers + hash-chained audit ledger).
  3. WORKFLOW — a Workflow drives the mission through phases.
  4. VERIFY   — each phase closes only on Iron-Law evidence.

The Engine takes a `verifier` callable: given a Phase, it returns Evidence.
In production that runs real commands/tests; in tests it's injected. This keeps
the Engine honest — it can never mark a phase done without asking the verifier
for proof, and it can never *start* a phase Shackle refuses to allow.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .roster import Roster
from .router import Assignment, Router
from .shackle import Governor, GovernorConfig
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
    hitl_required: bool = False
    governor: Governor | None = None

    @property
    def crew_names(self) -> list[str]:
        return [a.specialist.name for a in self.crew]

    @property
    def audit_intact(self) -> bool:
        """True iff the governance audit ledger has not been tampered with."""
        return self.governor is None or self.governor.ledger.verify()


class Engine:
    def __init__(
        self,
        roster: Roster | None = None,
        gate: VerificationGate | None = None,
        crew_size: int = 3,
        governor_config: GovernorConfig | None = None,
        phase_cost_usd: float = 0.0,
    ):
        self._roster = roster or Roster.load()
        self._router = Router(self._roster)
        self._gate = gate or VerificationGate()
        self._crew_size = crew_size
        self._governor_config = governor_config
        self._phase_cost_usd = phase_cost_usd

    def run(self, goal: str, verifier: Verifier) -> Mission:
        """Run a full mission. Never claims 'shipped' without (a) Shackle allowing
        each phase to start and (b) the Iron Law passing its evidence.

        Stops honestly at the first phase Shackle DENIES (policy/budget/loop),
        pauses if Shackle rules HITL, and blocks if the verifier's evidence
        fails the Iron Law. `shipped=True` only when every phase cleared both.
        """
        mission = Mission(goal=goal)
        mission.crew = self._router.route(goal, crew_size=self._crew_size)

        governor = Governor(self._governor_config)
        mission.governor = governor
        workflow = Workflow(gate=self._gate)

        while not workflow.shipped:
            phase = workflow.current

            # 2. GOVERN — may this phase run at all?
            verdict, reason = governor.evaluate(
                f"phase:{phase.value}", cost_usd=self._phase_cost_usd
            )
            if verdict == "DENY":
                mission.blocked_reason = f"{phase.value}: policy DENY — {reason}"
                mission.phase_log.append(f"{phase.value}: BLOCKED (policy) — {reason}")
                mission.shipped = False
                return mission
            if verdict == "HITL":
                mission.hitl_required = True
                mission.blocked_reason = f"{phase.value}: HITL required — {reason}"
                mission.phase_log.append(f"{phase.value}: PAUSED (HITL) — {reason}")
                mission.shipped = False
                return mission

            # 4. VERIFY — did the work actually pass?
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
