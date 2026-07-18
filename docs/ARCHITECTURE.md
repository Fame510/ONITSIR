# ONITSIR Architecture

ONITSIR is deliberately small and honest. Five modules, each owning one idea,
composed by an Engine. This document explains *why* it's shaped this way and how
the three source systems map onto the code.

## Design principles

1. **One responsibility per module.** Roster loads/searches; Router ranks;
   Verification judges evidence; Workflow sequences phases; Engine composes.
2. **The gate is not optional.** Every phase completion routes through the
   `VerificationGate`. There is no code path that marks a phase done without it.
3. **Honest failure over fake success.** When evidence fails the gate, the
   mission stops with a `blocked_reason`. It never degrades to a silent pass.
4. **No fabricated matches.** If no specialist scores against a goal, the Router
   returns an empty crew and the caller surfaces it — ONITSIR does not invent a
   plausible-looking expert.

## Module map

### `roster.py` — the workforce (from agency-agents)
- `Specialist`: an immutable playbook (id, name, category, description, keywords).
- `Roster`: loads `data/roster.json`, exposes `search()` with a transparent
  scoring model (category hit = 3, keyword hit = 2, name substring = 2).

### `router.py` — dispatch
- `Router.route(goal, crew_size)` tokenizes the goal, scores every specialist,
  returns the top-N as `Assignment`s with a `confidence` tier.

### `verification.py` — the Iron Law (from superpowers)
- `Evidence`: command + output + passed + timestamp.
- `VerificationGate.check()`: raises `VerificationError` unless the evidence is
  present, has a command, passed, has real output, and is *fresh* (not stale).

### `workflow.py` — the phase machine (from gsd-pro)
- `Phase`: `intake → spec → plan → build → verify → ship`.
- `Workflow.complete_current(evidence)`: gates the current phase, and only
  advances on success. Ships only when the final phase is verified.

### `engine.py` — the fusion
- `Engine.run(goal, verifier)`: routes a crew, then walks the workflow, asking
  the injected `verifier` for evidence at each phase and letting the gate decide.
- Dependency injection of the `verifier` is what keeps ONITSIR testable *and*
  honest: real deployments pass a verifier that runs commands; tests pass one
  that simulates pass/fail at chosen phases.

## Testing strategy

- **Unit**: each module in isolation (roster scoring, gate rules, phase order).
- **Integration**: `test_engine.py` proves the three layers fuse — a real crew is
  staffed from the roster, phases advance under the gate, and a failing phase
  blocks the ship.
- **CLI smoke**: `test_cli.py` exercises the user-facing commands.

Run `pytest` — 50 tests, all green.
