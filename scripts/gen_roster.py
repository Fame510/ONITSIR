#!/usr/bin/env python3
"""Generate ONITSIR roster.json — the 164-specialist workforce.

The 164 specialist playbooks become ONITSIR's
routable workforce. We derive lightweight routing keywords from each specialist's
category + name + description so the router can match a goal to the right experts.
"""
import json
import re
import sys
from pathlib import Path

STOPWORDS = {
    "the", "and", "for", "with", "expert", "specialist", "specializing", "focused",
    "masters", "master", "a", "an", "of", "in", "to", "on", "who", "that", "through",
    "building", "creating", "deep", "expertise", "strategic", "development", "based",
    "driven", "long", "term", "authentic", "value", "using", "into", "your", "their",
    "not", "by", "is", "are", "as", "at", "or",
}


def keywords(*texts: str) -> list[str]:
    tokens: list[str] = []
    for t in texts:
        for w in re.findall(r"[a-zA-Z][a-zA-Z0-9+#-]{2,}", (t or "").lower()):
            if w not in STOPWORDS and w not in tokens:
                tokens.append(w)
    return tokens[:24]


def main() -> int:
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    catalog = json.loads(src.read_text())
    roster = []
    for a in catalog:
        roster.append({
            "id": Path(a["path"]).stem,
            "name": a["name"],
            "category": a["category"],
            "description": a["desc"],
            "keywords": keywords(a["category"], a["name"], a["desc"]),
        })
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(roster, indent=2))
    cats = sorted({r["category"] for r in roster})
    print(f"Wrote {len(roster)} specialists to {dst} across {len(cats)} categories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
