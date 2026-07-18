"""ONITSIR — "On It, Sir." An AI agency operating system.

Four proprietary layers fused into one coherent product:

- **The Roster**: 164 specialist playbooks = the workforce.
- **The Governor**: a fail-closed policy surface that rules ALLOW / DENY / HITL
  on each action before it runs — budget, loop, and repeat circuit breakers plus
  a tamper-evident hash-chained audit ledger.
- **The Method**: spec -> plan -> build -> verify discipline, governed by the
  Iron Law — no completion without fresh verification evidence.
- **The Machine**: a phase state machine that drives a mission from intake to
  shipped, autonomously, one verified phase at a time.

Give ONITSIR a goal; it routes to the right specialists, checks each step past
the Governor, runs them through the verify-gated workflow, and ships. The bot
says "on it" — and means it.
"""
from .roster import Roster, Specialist
from .router import Router, Assignment
from .workflow import Workflow, Phase, PhaseStatus
from .verification import VerificationGate, Evidence, VerificationError
from .shackle import (
    decide, canonical_hash, Governor, GovernorConfig, AuditLedger, LedgerEntry,
)
from .engine import Engine, Mission

__version__ = "0.2.0"
__all__ = [
    "Roster", "Specialist",
    "Router", "Assignment",
    "Workflow", "Phase", "PhaseStatus",
    "VerificationGate", "Evidence", "VerificationError",
    "decide", "canonical_hash", "Governor", "GovernorConfig",
    "AuditLedger", "LedgerEntry",
    "Engine", "Mission",
]
