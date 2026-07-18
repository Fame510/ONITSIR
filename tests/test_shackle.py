"""Tests for Shackle — ONITSIR Governor layer (policy gate + audit ledger)."""
import pytest

from onitsir.shackle import (
    AuditLedger, Governor, GovernorConfig, canonical_hash, decide,
)


# ── canonical_hash ──────────────────────────────────────────────────────────
def test_canonical_hash_is_order_independent():
    a = canonical_hash({"query": "x", "error": "y"})
    b = canonical_hash({"error": "y", "query": "x"})
    assert a == b


def test_canonical_hash_rejects_nan():
    with pytest.raises(ValueError):
        canonical_hash({"x": float("nan")})


# ── decide() precedence — the policy surface ─────────────────────────────────
def test_decide_default_allows():
    assert decide({}, {}, {"tool_name": "t"}) == ("ALLOW", "within_thresholds")


def test_decide_malformed_denies_first():
    v, r = decide({}, {"circuit_tripped": True},
                  {"tool_name": "t", "params": {"__noncanonical__": True}})
    assert v == "DENY" and r == "policy_violation:malformed_input"


def test_decide_circuit_open_denies():
    assert decide({}, {"circuit_tripped": True}, {"tool_name": "t"}) == ("DENY", "circuit_open")


def test_decide_duplicate_nonce_denies():
    v, r = decide({}, {"seen_nonces": ["n1"]}, {"tool_name": "t", "nonce": "n1"})
    assert v == "DENY" and r == "policy_violation:duplicate_nonce"


def test_decide_budget_exhausted_denies():
    v, r = decide({"budget_usd": 1.0}, {"budget_remaining_usd": 0.0}, {"tool_name": "t"})
    assert v == "DENY" and r == "budget_exhausted"


def test_decide_max_repeat_denies():
    v, r = decide(
        {"max_repeat_calls": 3},
        {"repeat_counts": {"t": 3}, "last_tool_name": "t"},
        {"tool_name": "t"},
    )
    assert v == "DENY" and r == "max_repeat_exceeded"


def test_decide_hitl_always():
    assert decide({"hitl_mode": "always"}, {}, {"tool_name": "t"}) == ("HITL", "hitl_all_calls")


def test_decide_hitl_transition_approve_and_reject():
    assert decide({}, {"pending_transition": {"decision": "approve"}}, {"tool_name": "t"})[0] == "ALLOW"
    assert decide({}, {"pending_transition": {"decision": "reject"}}, {"tool_name": "t"})[0] == "DENY"


def test_decide_opaque_context_fails_closed_to_hitl():
    v, r = decide({}, {}, {"tool_name": "t", "params": {"ctx": "opaque"}})
    assert v == "HITL" and r == "fail_closed:opaque_context"


# ── hash-chained audit ledger ────────────────────────────────────────────────
def test_ledger_chain_intact():
    led = AuditLedger()
    led.append("a", "ALLOW", "ok")
    led.append("b", "DENY", "budget_exhausted")
    assert len(led) == 2
    assert led.verify() is True


def test_ledger_detects_tampering():
    led = AuditLedger()
    led.append("a", "ALLOW", "ok")
    led.append("b", "ALLOW", "ok")
    # Tamper with a past entry's verdict via object replacement.
    bad = led.entries
    object.__setattr__(led._entries[0], "verdict", "DENY")
    assert led.verify() is False


def test_ledger_links_prev_hash():
    led = AuditLedger()
    e0 = led.append("a", "ALLOW", "ok")
    e1 = led.append("b", "ALLOW", "ok")
    assert e1.prev_hash == e0.entry_hash


# ── runtime Governor ─────────────────────────────────────────────────────────
def test_governor_allows_within_budget():
    g = Governor(GovernorConfig(budget_usd=1.0))
    v, r = g.evaluate("phase:build", cost_usd=0.1)
    assert v == "ALLOW"
    assert g.remaining_usd == pytest.approx(0.9)


def test_governor_denies_when_budget_blown():
    g = Governor(GovernorConfig(budget_usd=0.10))
    v1, _ = g.evaluate("phase:a", cost_usd=0.05)  # remaining 0.05 -> allowed
    assert v1 == "ALLOW"
    v2, r2 = g.evaluate("phase:b", cost_usd=0.05)  # remaining 0.0 -> denied
    assert v2 == "DENY" and r2 == "budget_exhausted"


def test_governor_trips_circuit_after_deny():
    g = Governor(GovernorConfig(budget_usd=0.05))
    g.evaluate("phase:a", cost_usd=0.05)
    g.evaluate("phase:b")  # DENY budget -> trips circuit
    assert g.circuit_tripped is True
    v, r = g.evaluate("phase:c")
    assert v == "DENY" and r == "circuit_open"


def test_governor_repeat_breaker():
    g = Governor(GovernorConfig(max_repeat_calls=3, budget_usd=100.0))
    g.evaluate("same")
    g.evaluate("same")
    v, r = g.evaluate("same")  # third -> at ceiling
    assert v == "DENY" and r == "max_repeat_exceeded"


def test_governor_logs_every_decision_to_ledger():
    g = Governor(GovernorConfig(budget_usd=100.0))
    g.evaluate("a")
    g.evaluate("b")
    assert len(g.ledger) == 2
    assert g.ledger.verify() is True
