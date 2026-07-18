<div align="center">

<img src="assets/logo.png" alt="ONITSIR" width="360" />

# ONITSIR

### *"On It, Sir."* — an AI agency operating system.

**A remix of three systems into one product: a routable roster of 164 specialists, a verify‑gated workflow, and an autonomous phase machine.**

</div>

---

## What it is

Most "AI agent" setups give you either a pile of role prompts *or* a workflow — never both, wired together. ONITSIR fuses three of them into a single coherent engine:

| Layer | Role | Remixed from |
|---|---|---|
| **The Roster** | 164 specialist playbooks — the *workforce* you can route work to | `agency-agents` |
| **The Method** | spec → plan → build → **verify** discipline, enforced by the **Iron Law**: *no completion claim without fresh verification evidence* | `superpowers` |
| **The Machine** | an ordered phase state machine (`intake → spec → plan → build → verify → ship`) that drives a mission to completion, one verified phase at a time | `gsd-pro` |

Give ONITSIR a goal → it **routes** to the right specialists → drives them through the **verify‑gated workflow** → ships. It literally cannot report "done" on a phase without evidence that passes the gate.

## How the fusion works

```
        goal
         │
         ▼
   ┌───────────┐     picks the best-matching experts
   │  Router   │────▶ from the 164-specialist Roster
   └───────────┘
         │ crew
         ▼
   ┌───────────────────────────────────────────────┐
   │  Workflow (phase machine)                       │
   │  intake → spec → plan → build → verify → ship    │
   │      each phase completes ONLY when ...          │
   │            ┌──────────────────────┐              │
   │            │  Verification Gate    │  ◀── Iron Law│
   │            │  fresh + passing +    │              │
   │            │  real command output  │              │
   │            └──────────────────────┘              │
   └───────────────────────────────────────────────┘
         │
         ▼
   shipped ✔  (or honestly BLOCKED at the failing phase)
```

The Engine takes a **verifier** — a function that returns real evidence for each phase. In production that runs actual commands/tests; the gate independently validates the evidence is *fresh, passing, and backed by real output*. Fail the gate and the mission stops honestly at that phase — it never fakes a ship.

## Install

```bash
git clone https://github.com/Fame510/ONITSIR.git
cd ONITSIR
pip install -e .
```

## Usage

```bash
# See the workforce
onitsir roster

# Preview which specialists get staffed for a goal
onitsir crew "launch a reddit community growth campaign"

# Run a full mission end to end (demo verifier)
onitsir run "ship a digital product landing page"
```

```python
from onitsir import Engine
from onitsir.verification import Evidence

engine = Engine()

def verifier(phase):
    # run your real check for this phase, return the evidence
    return Evidence(command="pytest -q", output="50 passed", passed=True)

mission = engine.run("build an onboarding automation", verifier)
print(mission.shipped, mission.crew_names)
```

## Tested

The whole engine is covered by a vigorous suite — **50 tests, all passing** — spanning the roster, router, verification gate, workflow machine, the end‑to‑end engine, and the CLI. The gate tests specifically prove ONITSIR *refuses to ship* on missing, failing, or stale evidence.

```bash
pytest        # 50 passed
```

## Project layout

```
onitsir/
  roster.py        # load + search the 164 specialists
  router.py        # goal -> ranked crew
  verification.py  # the Iron Law gate
  workflow.py      # the phase state machine
  engine.py        # fuses all three into a mission
  cli.py           # onitsir command
data/roster.json   # the workforce
tests/             # 50 tests
```

## License

MIT © Fame510
