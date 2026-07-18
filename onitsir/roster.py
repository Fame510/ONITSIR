"""The Roster — ONITSIR's specialist workforce.

Loads the 164 specialist playbooks and exposes keyword/category search so the
Router can match a goal to the right experts.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_ROSTER = Path(__file__).resolve().parent.parent / "data" / "roster.json"


@dataclass(frozen=True)
class Specialist:
    """A single specialist playbook from the roster."""
    id: str
    name: str
    category: str
    description: str
    keywords: tuple[str, ...] = field(default_factory=tuple)

    def score(self, terms: list[str]) -> int:
        """How well this specialist matches a set of lowercased query terms.

        Keyword hit = 2 points; category hit = 3 points (a category match is a
        strong domain signal); name substring hit = 2 points.
        """
        score = 0
        kw = set(self.keywords)
        cat = self.category.lower()
        name = self.name.lower()
        for t in terms:
            if t in kw:
                score += 2
            if t == cat or t in cat:
                score += 3
            if t in name:
                score += 2
        return score


class Roster:
    """The full set of specialists, loaded from roster.json."""

    def __init__(self, specialists: list[Specialist]):
        if not specialists:
            raise ValueError("Roster cannot be empty — no specialists loaded.")
        self._specialists = specialists
        self._by_id = {s.id: s for s in specialists}

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Roster":
        p = Path(path) if path else _DEFAULT_ROSTER
        if not p.exists():
            raise FileNotFoundError(f"Roster data not found at {p}")
        raw = json.loads(p.read_text())
        specialists = [
            Specialist(
                id=str(r["id"]),
                name=str(r["name"]),
                category=str(r["category"]),
                description=str(r.get("description", "")),
                keywords=tuple(r.get("keywords", [])),
            )
            for r in raw
        ]
        return cls(specialists)

    def __len__(self) -> int:
        return len(self._specialists)

    def all(self) -> list[Specialist]:
        return list(self._specialists)

    def categories(self) -> list[str]:
        return sorted({s.category for s in self._specialists})

    def get(self, specialist_id: str) -> Specialist:
        if specialist_id not in self._by_id:
            raise KeyError(f"No specialist with id {specialist_id!r}")
        return self._by_id[specialist_id]

    def search(self, query: str, limit: int = 5) -> list[tuple[Specialist, int]]:
        """Return up to `limit` (specialist, score) pairs, best match first.

        Only positive-scoring specialists are returned.
        """
        terms = [t for t in _tokenize(query)]
        scored = [(s, s.score(terms)) for s in self._specialists]
        scored = [(s, sc) for s, sc in scored if sc > 0]
        scored.sort(key=lambda pair: (-pair[1], pair[0].name))
        return scored[:limit]


def _tokenize(text: str) -> list[str]:
    import re
    return [w for w in re.findall(r"[a-zA-Z][a-zA-Z0-9+#-]{1,}", text.lower())]
