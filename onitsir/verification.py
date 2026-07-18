"""The Verification Gate — the Iron Law (remix source: superpowers).

superpowers' core discipline: "NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION
EVIDENCE." This module encodes that as an actual gate a phase must pass before it
can be marked complete. A phase cannot claim success on vibes — it must attach
evidence (a command + its output + a passing signal) that the gate validates.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


class VerificationError(Exception):
    """Raised when a completion is claimed without valid evidence."""


@dataclass(frozen=True)
class Evidence:
    """Proof that a phase actually did what it claims.

    - `command`: what was run to prove the claim (e.g. a test command).
    - `output`: the real output produced.
    - `passed`: the objectively-checked pass signal (e.g. exit code == 0).
    - `at`: capture timestamp; the gate rejects stale evidence.
    """
    command: str
    output: str
    passed: bool
    at: float = field(default_factory=time.time)


class VerificationGate:
    """Validates evidence before any completion claim is allowed through.

    `max_age_s` enforces *fresh* evidence — the Iron Law rejects "it passed
    earlier". Set to None to disable the freshness check (not recommended).
    """

    def __init__(self, max_age_s: float | None = 3600.0):
        self.max_age_s = max_age_s

    def check(self, evidence: Evidence | None) -> None:
        """Raise VerificationError unless evidence justifies a success claim."""
        if evidence is None:
            raise VerificationError(
                "Iron Law: cannot claim completion — no verification evidence attached."
            )
        if not evidence.command or not evidence.command.strip():
            raise VerificationError("Iron Law: evidence has no command to prove the claim.")
        if not evidence.passed:
            raise VerificationError(
                "Iron Law: evidence shows the check did NOT pass — completion refused."
            )
        if not evidence.output or not evidence.output.strip():
            raise VerificationError("Iron Law: evidence has no captured output to inspect.")
        if self.max_age_s is not None:
            age = time.time() - evidence.at
            if age > self.max_age_s:
                raise VerificationError(
                    f"Iron Law: evidence is stale ({age:.0f}s old > {self.max_age_s:.0f}s). "
                    "Re-run the verification."
                )

    def is_satisfied(self, evidence: Evidence | None) -> bool:
        try:
            self.check(evidence)
            return True
        except VerificationError:
            return False
