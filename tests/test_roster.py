"""Tests for the Roster."""
import pytest

from onitsir.roster import Roster, Specialist, _tokenize


def test_roster_loads_full_workforce(roster):
    # The roster must carry the entire specialist library, not a subset.
    assert len(roster) == 164


def test_roster_has_expected_categories(roster):
    cats = roster.categories()
    assert "marketing" in cats
    assert "engineering" in cats
    assert "sales" in cats
    assert len(cats) == 14


def test_every_specialist_is_well_formed(roster):
    for s in roster.all():
        assert s.id and isinstance(s.id, str)
        assert s.name and isinstance(s.name, str)
        assert s.category and isinstance(s.category, str)
        assert isinstance(s.keywords, tuple)


def test_ids_are_unique(roster):
    ids = [s.id for s in roster.all()]
    assert len(ids) == len(set(ids))


def test_get_by_id_roundtrip(roster):
    first = roster.all()[0]
    assert roster.get(first.id) is first


def test_get_unknown_id_raises(roster):
    with pytest.raises(KeyError):
        roster.get("no-such-specialist")


def test_empty_roster_rejected():
    with pytest.raises(ValueError):
        Roster([])


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        Roster.load(tmp_path / "nope.json")


def test_search_marketing_goal_returns_marketing_specialist(roster):
    results = roster.search("reddit community engagement marketing", limit=5)
    assert results, "expected at least one match"
    top = results[0][0]
    # The top hit for a reddit/marketing goal should live in marketing.
    assert top.category == "marketing"


def test_search_is_ranked_descending(roster):
    results = roster.search("engineering backend api", limit=10)
    scores = [sc for _, sc in results]
    assert scores == sorted(scores, reverse=True)


def test_search_only_returns_positive_scores(roster):
    results = roster.search("qwqzxjkl nonsense termzzz", limit=5)
    assert results == []


def test_search_respects_limit(roster):
    results = roster.search("content social media growth", limit=2)
    assert len(results) <= 2


def test_specialist_scoring_rewards_category_and_keyword():
    s = Specialist(
        id="x", name="Growth Hacker", category="marketing",
        description="growth", keywords=("growth", "funnel", "viral"),
    )
    assert s.score(["marketing"]) >= 3          # category hit
    assert s.score(["funnel"]) >= 2             # keyword hit
    assert s.score(["growth"]) > s.score(["nomatch"])


def test_tokenize_lowercases_and_filters():
    toks = _tokenize("Build a REST API!!")
    assert "rest" in toks
    assert "api" in toks
    assert all(t == t.lower() for t in toks)
