"""ONITSIR command-line interface.

Usage:
    onitsir roster                       # show roster size + categories
    onitsir crew "goal text"             # preview which specialists get staffed
    onitsir run  "goal text"             # run a demo mission (auto-verified)

`run` uses a demo verifier that produces passing evidence for each phase so you
can see the full workflow end to end. Real deployments inject a verifier that
runs actual commands/tests — the Engine cannot ship without passing the gate.
"""
from __future__ import annotations

import argparse
import sys

from .engine import Engine
from .roster import Roster
from .verification import Evidence
from .workflow import Phase

TAGLINE = 'ONITSIR — "On It, Sir."'


def _demo_verifier(phase: Phase) -> Evidence:
    return Evidence(
        command=f"onitsir selfcheck --phase {phase.value}",
        output=f"[{phase.value}] demo check: 1 passed, 0 failed",
        passed=True,
    )


def cmd_roster(args: argparse.Namespace) -> int:
    roster = Roster.load(args.data)
    print(f"{TAGLINE}\nRoster: {len(roster)} specialists across {len(roster.categories())} categories")
    for c in roster.categories():
        n = sum(1 for s in roster.all() if s.category == c)
        print(f"  - {c}: {n}")
    return 0


def cmd_crew(args: argparse.Namespace) -> int:
    engine = Engine(roster=Roster.load(args.data), crew_size=args.crew_size)
    crew = engine.preview_crew(args.goal)
    print(f"{TAGLINE}\nGoal: {args.goal}\n")
    if not crew:
        print("No confident specialist match — refine the goal or broaden the roster.")
        return 1
    print("Staffed crew:")
    for a in crew:
        print(f"  [{a.confidence:>6}] {a.specialist.name}  ({a.specialist.category})")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    engine = Engine(roster=Roster.load(args.data), crew_size=args.crew_size)
    mission = engine.run(args.goal, verifier=_demo_verifier)
    print(f"{TAGLINE}\nGoal: {mission.goal}")
    print(f"Crew: {', '.join(mission.crew_names) or '(none matched)'}\n")
    for line in mission.phase_log:
        print(f"  {line}")
    print()
    if mission.shipped:
        print("Mission SHIPPED — every phase passed the Iron Law gate. On it, done.")
        return 0
    print(f"Mission BLOCKED — {mission.blocked_reason}")
    return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="onitsir", description=TAGLINE)
    p.add_argument("--data", default=None, help="Path to roster.json (optional)")
    p.add_argument("--crew-size", type=int, default=3, help="Specialists per mission")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("roster", help="Show roster stats").set_defaults(func=cmd_roster)
    c = sub.add_parser("crew", help="Preview staffed crew for a goal")
    c.add_argument("goal")
    c.set_defaults(func=cmd_crew)
    r = sub.add_parser("run", help="Run a demo mission end to end")
    r.add_argument("goal")
    r.set_defaults(func=cmd_run)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
