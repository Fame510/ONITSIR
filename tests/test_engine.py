"""End-to-end Engine tests — proof the three systems fuse into one product."""
import pytest

from onitsir.engine import Engine
from onitsir.verification import Evidence, VerificationGate
from onitsir.workflow import Phase


def _always_pass(phase: Phase) -> Evidence:
    return Evidence(command=f"verify {phase.value}", output="1 passed", passed=True)


def _fail_at(target: Phase):
    def verifier(phase: Phase) -> Evidence:
        passed = phase != target
        return Evidence(
            command=f"verify {phase.value}",
            output="ok" if passed else "boom: 1 failed",
            passed=passed,
        )
    return verifier


def test_mission_ships_when_all_phases_pass(roster):
    engine = Engine(roster=roster)
    m = engine.run("launch a reddit community growth marketing campaign", _always_pass)
    assert m.shipped is True
    assert m.blocked_reason is None
    # every phase logged as verified
    assert sum("verified" in line for line in m.phase_log) == len(Phase.ordered())


def test_mission_staffs_a_real_crew_from_the_roster(roster):
    engine = Engine(roster=roster)
    m = engine.run("engineering: build a backend api with database", _always_pass)
    assert m.crew, "crew should be staffed from the 164-specialist roster"
    assert all(a.specialist.name for a in m.crew)


def test_mission_blocks_honestly_when_a_phase_fails(roster):
    engine = Engine(roster=roster)
    m = engine.run("ship a digital product", _fail_at(Phase.BUILD))
    assert m.shipped is False
    assert m.blocked_reason is not None
    assert "build" in m.blocked_reason
    # phases before BUILD were verified; BUILD is where it stopped
    assert any("build: BLOCKED" in line for line in m.phase_log)


def test_engine_never_ships_past_a_failed_gate(roster):
    # Fail at the very first phase — nothing should ship.
    engine = Engine(roster=roster)
    m = engine.run("anything", _fail_at(Phase.INTAKE))
    assert m.shipped is False
    assert m.phase_log[-1].startswith("intake: BLOCKED")


def test_preview_crew_does_not_execute(roster):
    engine = Engine(roster=roster)
    crew = engine.preview_crew("social media content strategy")
    assert isinstance(crew, list)


def test_engine_respects_custom_gate(roster):
    import time
    # A gate that rejects everything stale; feed stale evidence -> block at intake.
    engine = Engine(roster=roster, gate=VerificationGate(max_age_s=1))

    def stale_verifier(phase: Phase) -> Evidence:
        return Evidence(command="c", output="ok", passed=True, at=time.time() - 9999)

    m = engine.run("goal", stale_verifier)
    assert m.shipped is False


def test_crew_names_helper(roster):
    engine = Engine(roster=roster)
    m = engine.run("marketing growth content", _always_pass)
    assert m.crew_names == [a.specialist.name for a in m.crew]
