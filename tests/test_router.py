"""Tests for the Router (dispatch layer)."""
import pytest

from onitsir.router import Router, Assignment


def test_route_empty_goal_raises(roster):
    r = Router(roster)
    with pytest.raises(ValueError):
        r.route("")
    with pytest.raises(ValueError):
        r.route("   ")


def test_route_bad_crew_size_raises(roster):
    r = Router(roster)
    with pytest.raises(ValueError):
        r.route("marketing", crew_size=0)


def test_route_returns_assignments(roster):
    r = Router(roster)
    crew = r.route("reddit community marketing growth", crew_size=3)
    assert crew
    assert all(isinstance(a, Assignment) for a in crew)
    assert len(crew) <= 3


def test_route_respects_crew_size(roster):
    r = Router(roster)
    crew = r.route("content social media video", crew_size=1)
    assert len(crew) <= 1


def test_route_no_match_returns_empty_not_garbage(roster):
    r = Router(roster)
    crew = r.route("zzzq nonsense unmatchable termxyz")
    assert crew == []


def test_assignments_sorted_by_score_desc(roster):
    r = Router(roster)
    crew = r.route("engineering api backend database", crew_size=5)
    scores = [a.score for a in crew]
    assert scores == sorted(scores, reverse=True)


def test_confidence_tiers():
    from onitsir.roster import Specialist
    s = Specialist(id="x", name="n", category="c", description="d")
    assert Assignment(s, 9).confidence == "high"
    assert Assignment(s, 5).confidence == "medium"
    assert Assignment(s, 2).confidence == "low"
