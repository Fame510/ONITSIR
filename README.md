<div align="center">

<img src="assets/logo.png" alt="ONITSIR" width="360" />

# ONITSIR

### *"On It, Sir."* — the AI agency operating system.

**One system that routes work to 164 specialists, governs every action behind a fail-closed policy gate, drives it through a verify-gated workflow, and ships — autonomously. Nothing else on the market does all four in one engine.**

</div>

---

## What it is

"AI agent" tools give you *one* of these things. ONITSIR is the first to fuse all four into a single coherent engine — a workforce, a governor, a method, and a machine:

| Layer | What it does |
|---|---|
| **The Roster** | 164 specialist playbooks — the workforce. A router scores your goal and staffs the best-matched crew. |
| **The Governor** | A fail-closed policy surface that rules **ALLOW / DENY / HITL** on every action *before* it runs — budget, loop, and repeat circuit breakers plus a tamper-evident, hash-chained audit ledger. |
| **The Method** | The **Iron Law**: spec -> plan -> build -> **verify**. No phase is ever "done" without fresh, passing, real evidence. |
| **The Machine** | An ordered phase state machine (`intake -> spec -> plan -> build -> verify -> ship`) that drives a mission to completion, one verified phase at a time. |

Give ONITSIR a goal -> it **staffs** the right specialists -> **governs** each step past the policy gate -> drives them through the **verify-gated workflow** -> ships. It literally cannot report "done" without both gates passing.

## Why it's different

Plenty of frameworks route to role-prompts. Plenty have a workflow. A rare few verify their own output. **None of them put a real-time governance gate — budget/loop breakers, ALLOW/DENY/HITL rulings, and a cryptographic audit ledger — in front of a verify-gated, autonomous phase machine staffed by a 164-specialist roster.** That combination is ONITSIR.

## How the engine works

```
        goal
         |
         v
   +-----------+     picks the best-matching experts
   |  Router   |----> from the 164-specialist Roster
   +-----------+
         | crew
         v
   +-------------------------------------------------+
   |  Workflow (phase machine)                        |
   |  intake -> spec -> plan -> build -> verify -> ship|
   |   each phase must clear TWO gates, in order:      |
   |     +-----------------------+  <- the Governor     |
   |     | Governor: may it run? |   ALLOW/DENY/HITL    |
   |     | budget . loop . repeat|   + audit ledger     |
   |     +-----------------------+                      |
   |     +-----------------------+  <- the Iron Law      |
   |     | Gate: did it pass?    |   fresh + passing     |
   |     | real command output   |   evidence            |
   |     +-----------------------+                      |
   +-------------------------------------------------+
         |
         v
   shipped  (or honestly BLOCKED / PAUSED at the failing phase)
```

The Engine takes a **verifier** — a function that returns real evidence for each phase. In production that runs actual commands/tests; the Iron-Law gate independently validates the evidence is *fresh, passing, and backed by real output*. Fail a gate and the mission stops honestly at that phase — it never fakes a ship.

## Live demo

The landing page runs the **entire engine in your browser** — routing, governance, workflow, and verification, live. Try a mission at the hosted site (GitHub Pages), or run it locally below.

## Install

```bash
git clone https://github.com/Fame510/ONITSIR.git
cd ONITSIR
pip install -e .
```

## Usage

```bash
onitsir roster                                    # the 164-specialist workforce
onitsir crew    "launch a reddit growth campaign" # preview the staffed crew
onitsir shackle                                   # watch the Governor rule ALLOW/DENY/HITL
onitsir run     "ship a digital product"          # run a full mission end to end
```

```python
from onitsir import Engine, GovernorConfig
from onitsir.verification import Evidence

engine = Engine(governor_config=GovernorConfig(budget_usd=5.0), phase_cost_usd=0.25)

def verifier(phase):
    return Evidence(command="pytest -q", output="75 passed", passed=True)

mission = engine.run("build an onboarding automation", verifier)
print(mission.shipped, mission.crew_names, mission.audit_intact)
```

## Tested

The whole engine is covered by a vigorous suite — **75 tests, all passing** — spanning the roster, router, the Governor policy gate + hash-chained ledger, the Iron-Law verification gate, the workflow machine, the end-to-end engine, and the CLI. The gate tests specifically prove ONITSIR *refuses to ship* on missing, failing, or stale evidence, and *refuses to run* when the Governor says DENY.

```bash
pytest        # 75 passed
```

## Project layout

```
onitsir/
  roster.py        # load + search the 164 specialists
  router.py        # goal -> ranked crew
  shackle.py       # the Governor: policy surface + hash-chained audit ledger
  verification.py  # the Iron Law gate
  workflow.py      # the phase state machine
  engine.py        # fuses all four layers into a mission
  cli.py           # onitsir command
site/              # the in-browser app (GitHub Pages)
data/roster.json   # the workforce
tests/             # 75 tests
```

## License

MIT (c) Fame510
