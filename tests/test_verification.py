"""Tests for the Verification Gate — the Iron Law."""
import time

import pytest

from onitsir.verification import Evidence, VerificationGate, VerificationError


def _good() -> Evidence:
    return Evidence(command="pytest -q", output="42 passed", passed=True)


def test_valid_evidence_passes():
    VerificationGate().check(_good())  # should not raise


def test_none_evidence_rejected():
    with pytest.raises(VerificationError):
        VerificationGate().check(None)


def test_not_passed_rejected():
    ev = Evidence(command="pytest", output="1 failed", passed=False)
    with pytest.raises(VerificationError):
        VerificationGate().check(ev)


def test_empty_command_rejected():
    ev = Evidence(command="   ", output="ok", passed=True)
    with pytest.raises(VerificationError):
        VerificationGate().check(ev)


def test_empty_output_rejected():
    ev = Evidence(command="pytest", output="", passed=True)
    with pytest.raises(VerificationError):
        VerificationGate().check(ev)


def test_stale_evidence_rejected():
    ev = Evidence(command="pytest", output="ok", passed=True, at=time.time() - 10_000)
    with pytest.raises(VerificationError):
        VerificationGate(max_age_s=3600).check(ev)


def test_fresh_evidence_within_window_ok():
    ev = Evidence(command="pytest", output="ok", passed=True, at=time.time() - 5)
    VerificationGate(max_age_s=3600).check(ev)


def test_freshness_disabled_allows_old_evidence():
    ev = Evidence(command="pytest", output="ok", passed=True, at=time.time() - 999_999)
    VerificationGate(max_age_s=None).check(ev)


def test_is_satisfied_boolean():
    gate = VerificationGate()
    assert gate.is_satisfied(_good()) is True
    assert gate.is_satisfied(None) is False
