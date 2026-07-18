"""ONITSIR · Shackle v1 — the Governor layer.

This is ONITSIR's governance gate: a real-time policy decision surface that
rules ALLOW / DENY / HITL on every action *before* it runs, plus budget,
loop-of-death, and repeat-call circuit breakers and a tamper-evident,
hash-chained audit ledger.

Shackle is ONITSIR's governance layer — it sits IN FRONT OF the Iron-Law
verification gate:

    goal → route → [ Shackle: may this run? ] → run → [ Iron Law: did it pass? ] → ship

Where the verification gate answers "did the work actually pass?", Shackle
answers the prior question "is this action allowed to happen at all?" — the
guardrail that keeps an autonomous mission inside budget, out of infinite
loops, and behind a human when policy demands it.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

Verdict = str  # "ALLOW" | "DENY" | "HITL"


# ──────────────────────────────────────────────────────────────────────────
# Canonicalization + the policy decision surface (pure, stdlib-only)
# ──────────────────────────────────────────────────────────────────────────
def canonical_hash(params: Dict[str, Any]) -> str:
    """SHA-256 over canonical JSON: keys sorted, tight separators, UTF-8.

    NaN/Infinity and non-string keys are rejected (allow_nan=False), which
    callers treat as malformed input.
    """
    serialized = json.dumps(
        params, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def decide(
    config: Dict[str, Any],
    state: Dict[str, Any],
    call: Dict[str, Any],
) -> Tuple[Verdict, str]:
    """Return (verdict, reason) for a single action. Fail-closed by construction.

    Precedence (highest first):
      1. malformed / non-canonicalizable input        -> DENY
      2. circuit already open                          -> DENY
      3. duplicate nonce (replay)                      -> DENY
      4. HITL transition contract (pending_transition) -> ALLOW/DENY/HITL
      5. budget exhausted                              -> DENY
      6. max repeat exceeded                           -> DENY
      7. HITL mode 'always'                            -> HITL
      8. HITL budget threshold                         -> HITL
      9. opaque / untestable context                   -> HITL (fail-closed)
     10. default                                       -> ALLOW
    """
    params: Dict[str, Any] = call.get("params", {}) or {}
    pending = state.get("pending_transition")

    # 1. malformed / non-canonicalizable input
    if params.get("__noncanonical__") is True:
        return ("DENY", "policy_violation:malformed_input")

    # 2. circuit already open
    if state.get("circuit_tripped") is True:
        return ("DENY", "circuit_open")

    # 3. duplicate nonce (replay)
    seen = state.get("seen_nonces") or []
    nonce = call.get("nonce")
    if nonce is not None and nonce in seen:
        if (
            pending
            and pending.get("resume_attempt") is True
            and pending.get("terminal_status") in ("rejected", "superseded")
        ):
            return ("DENY", "policy_violation:duplicate_resume_no_effect")
        return ("DENY", "policy_violation:duplicate_nonce")

    # 4. HITL transition contract
    if pending:
        decision = pending.get("decision")
        if decision == "approve":
            return ("ALLOW", "hitl_transition:approve")
        if decision == "reject":
            return ("DENY", "hitl_transition:reject")
        if decision == "modify":
            return ("ALLOW", "hitl_transition:modify_successor")
        if decision in ("defer", "escalate"):
            return ("HITL", "hitl_transition:defer_escalate")

    # 5. budget exhausted
    budget = config.get("budget_usd", 0) or 0
    remaining = state.get("budget_remaining_usd")
    if remaining is not None and remaining <= 0 and budget > 0:
        return ("DENY", "budget_exhausted")

    # 6. max repeat exceeded
    max_repeat = config.get("max_repeat_calls")
    repeat_counts = state.get("repeat_counts")
    last_tool = state.get("last_tool_name")
    if max_repeat is not None and repeat_counts and last_tool:
        rc = repeat_counts.get(call.get("tool_name"))
        if rc is not None and rc >= max_repeat and last_tool == call.get("tool_name"):
            return ("DENY", "max_repeat_exceeded")

    # 7. HITL always
    if config.get("hitl_mode") == "always":
        return ("HITL", "hitl_all_calls")

    # 8. HITL budget threshold
    if config.get("hitl_mode") == "on_threshold" and config.get("hitl_budget_threshold") is not None:
        initial = state.get("budget_initial_usd")
        if initial:
            frac = state.get("budget_remaining_usd", 0) / initial
            if frac <= config["hitl_budget_threshold"]:
                return ("HITL", "budget_threshold")

    # 9. opaque / untestable context
    if params.get("ctx") == "opaque":
        return ("HITL", "fail_closed:opaque_context")

    # 10. default allow
    return ("ALLOW", "within_thresholds")


# ──────────────────────────────────────────────────────────────────────────
# Tamper-evident, hash-chained audit ledger
# ──────────────────────────────────────────────────────────────────────────
GENESIS = "0" * 64


@dataclass(frozen=True)
class LedgerEntry:
    index: int
    at: float
    tool_name: str
    verdict: Verdict
    reason: str
    prev_hash: str
    entry_hash: str


class AuditLedger:
    """Append-only ledger where each entry commits to the previous one's hash.

    Any mutation of a past entry breaks the chain — `verify()` detects it.
    """

    def __init__(self) -> None:
        self._entries: List[LedgerEntry] = []

    @staticmethod
    def _hash(index: int, at: float, tool_name: str, verdict: str,
              reason: str, prev_hash: str) -> str:
        return canonical_hash({
            "index": index, "at": at, "tool_name": tool_name,
            "verdict": verdict, "reason": reason, "prev_hash": prev_hash,
        })

    def append(self, tool_name: str, verdict: Verdict, reason: str,
               at: Optional[float] = None) -> LedgerEntry:
        at = time.time() if at is None else at
        index = len(self._entries)
        prev_hash = self._entries[-1].entry_hash if self._entries else GENESIS
        entry_hash = self._hash(index, at, tool_name, verdict, reason, prev_hash)
        entry = LedgerEntry(index, at, tool_name, verdict, reason, prev_hash, entry_hash)
        self._entries.append(entry)
        return entry

    def verify(self) -> bool:
        """True iff the whole chain is intact (no entry has been tampered with)."""
        prev = GENESIS
        for i, e in enumerate(self._entries):
            if e.index != i or e.prev_hash != prev:
                return False
            expected = self._hash(e.index, e.at, e.tool_name, e.verdict, e.reason, e.prev_hash)
            if expected != e.entry_hash:
                return False
            prev = e.entry_hash
        return True

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def entries(self) -> List[LedgerEntry]:
        return list(self._entries)

    @property
    def head(self) -> str:
        return self._entries[-1].entry_hash if self._entries else GENESIS


# ──────────────────────────────────────────────────────────────────────────
# Runtime Governor — live state + circuit breakers, wired to decide()
# ──────────────────────────────────────────────────────────────────────────
@dataclass
class GovernorConfig:
    budget_usd: float = 1.0
    max_repeat_calls: int = 3
    hitl_mode: Optional[str] = None            # None | "always" | "on_threshold"
    hitl_budget_threshold: Optional[float] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "budget_usd": self.budget_usd,
            "max_repeat_calls": self.max_repeat_calls,
            "hitl_mode": self.hitl_mode,
            "hitl_budget_threshold": self.hitl_budget_threshold,
        }


class Governor:
    """Stateful policy runtime. Feeds live telemetry into the pure decide()
    surface and keeps a hash-chained audit ledger of every ruling."""

    def __init__(self, config: GovernorConfig | None = None) -> None:
        self.config = config or GovernorConfig()
        self.spent_usd: float = 0.0
        self.repeat_counts: Dict[str, int] = {}
        self.seen_nonces: List[str] = []
        self.circuit_tripped: bool = False
        self.last_tool_name: Optional[str] = None
        self.ledger = AuditLedger()

    def _state(self) -> Dict[str, Any]:
        return {
            "circuit_tripped": self.circuit_tripped,
            "seen_nonces": list(self.seen_nonces),
            "budget_initial_usd": self.config.budget_usd,
            "budget_remaining_usd": max(self.config.budget_usd - self.spent_usd, 0.0),
            "repeat_counts": dict(self.repeat_counts),
            "last_tool_name": self.last_tool_name,
        }

    def evaluate(self, tool_name: str, *, cost_usd: float = 0.0,
                 nonce: Optional[str] = None,
                 params: Optional[Dict[str, Any]] = None) -> Tuple[Verdict, str]:
        """Rule on one action and record it. Updates live state first so budget
        and repeat breakers reflect *this* call, then consults decide()."""
        self.spent_usd += cost_usd
        self.repeat_counts[tool_name] = self.repeat_counts.get(tool_name, 0) + 1
        self.last_tool_name = tool_name

        call: Dict[str, Any] = {"tool_name": tool_name, "params": params or {}}
        if nonce is not None:
            call["nonce"] = nonce

        verdict, reason = decide(self.config.as_dict(), self._state(), call)

        if nonce is not None and nonce not in self.seen_nonces:
            self.seen_nonces.append(nonce)
        if verdict == "DENY":
            self.circuit_tripped = True

        self.ledger.append(tool_name, verdict, reason)
        return verdict, reason

    @property
    def remaining_usd(self) -> float:
        return max(self.config.budget_usd - self.spent_usd, 0.0)
