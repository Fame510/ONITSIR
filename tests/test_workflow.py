"""Tests for the Workflow machine (gsd-pro remix layer) + its fusion with the gate."""
import pytest

from onitsir.verification import Evidence, VerificationError, VerificationGate
from onitsir.workflow import Phase, PhaseStatus, Workflow


def _ev() -> Evidence:
    return Evidence(command="check", output="ok: passed", passed=True)


def test_phase_order():
    assert Phase.ordered() == [
        Phase.INTAKE, Phase.SPEC, Phase.PLAN, Phase.BUILD, Phase.VERIFY, Phase.SHIP
    ]


def test_starts_at_intake_active():
    wf = Workflow()
    assert wf.current == Phase.INTAKE
    assert wf.record(Phase.INTAKE).status == PhaseStatus.ACTIVE


def test_complete_advances_phase():
    wf = Workflow()
    nxt = wf.complete_current(_ev())
    assert nxt == Phase.SPEC
    assert wf.record(Phase.INTAKE).status == PhaseStatus.VERIFIED


def test_cannot_ship_without_walking_every_phase():
    wf = Workflow()
    for _ in range(len(Phase.ordered()) - 1):
        assert not wf.shipped
        wf.complete_current(_ev())
    # last phase (SHIP) still needs its own completion
    assert wf.current == Phase.SHIP
    assert not wf.shipped
    wf.complete_current(_ev())
    assert wf.shipped


def test_bad_evidence_blocks_and_does_not_advance():
    wf = Workflow()
    bad = Evidence(command="check", output="fail", passed=False)
    with pytest.raises(VerificationError):
        wf.complete_current(bad)
    # still on INTAKE, still active — no silent advance
    assert wf.current == Phase.INTAKE
    assert wf.record(Phase.INTAKE).status == PhaseStatus.ACTIVE


def test_progress_snapshot_shape():
    wf = Workflow()
    wf.complete_current(_ev())
    prog = wf.progress()
    assert prog["intake"] == "verified"
    assert prog["spec"] == "active"
    assert prog["ship"] == "pending"


def test_verified_count_increments():
    wf = Workflow()
    assert wf.verified_count() == 0
    wf.complete_current(_ev())
    wf.complete_current(_ev())
    assert wf.verified_count() == 2


def test_workflow_uses_injected_gate_freshness():
    import time
    strict = VerificationGate(max_age_s=1)
    wf = Workflow(gate=strict)
    stale = Evidence(command="c", output="ok", passed=True, at=time.time() - 100)
    with pytest.raises(VerificationError):
        wf.complete_current(stale)
