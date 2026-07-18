"""ONITSIR — "On It, Sir." An AI agency operating system.

A remix of three systems into one coherent product:

- **The Roster** (from `agency-agents`): 164 specialist playbooks = the workforce.
- **The Method** (from `superpowers`): spec -> plan -> build -> verify discipline,
  governed by the Iron Law — no completion without fresh verification evidence.
- **The Machine** (from `gsd-pro`): a phase state machine that drives a mission
  from intake to shipped, autonomously, one verified phase at a time.

Give ONITSIR a goal; it routes to the right specialists, runs them through the
verify-gated workflow, and ships. The bot says "on it" — and means it.
"""
from .roster import Roster, Specialist
from .router import Router, Assignment
from .workflow import Workflow, Phase, PhaseStatus
from .verification import VerificationGate, Evidence, VerificationError
from .engine import Engine, Mission

__version__ = "0.1.0"
__all__ = [
    "Roster", "Specialist",
    "Router", "Assignment",
    "Workflow", "Phase", "PhaseStatus",
    "VerificationGate", "Evidence", "VerificationError",
    "Engine", "Mission",
]
