# 🚨 War Room — a band of AI agents that runs your incident response

> When a production service breaks, a team of specialized AI agents triages, diagnoses, and fixes the incident — **coordinating entirely through [Band](https://band.ai)** — while a human holds the only key to the remediation.

**Built for the [lablab.ai](https://lablab.ai) · Band of Agents Hackathon.**

A full incident — detect → diagnose → **block → human-approve** → heal — runs end-to-end in under a minute, and every handoff between agents is a real Band message. There is no orchestrator, no message bus, no shared memory. **Band is the nervous system.**

---

## The incident, start to finish

```
Detector      ->  @commander     ALERT checkout error_rate 42%
Commander     ->  @diagnostician investigate  +  @comms post update
Diagnostician ->  root cause: deploy dpl-104, NullPointer in PricingService
Remediator    ->  rollback dpl-104        [ BLOCKED — human approval required ]
Commander     ->  APPROVAL REQUESTED: rollback dpl-104 on checkout
                  ── human clicks APPROVE on the dashboard ──
Server        ->  rollback dpl-104        [ OK ] checkout healthy
Commander     ->  INCIDENT RESOLVED
```

## Six participants, one Band room

| Agent | Role | Powered by |
|---|---|---|
| **Detector** | Watches service metrics; raises the alert that starts everything | deterministic (non-LLM) |
| **Commander** | Opens the incident, delegates, declares resolved | LLM — coordinate only |
| **Diagnostician** | Pulls metrics / logs / deploys, pins the root cause | LLM + read tools |
| **Remediator** | Proposes the fix; it runs **only after a human approves** | LLM + action tools |
| **Comms** | Posts plain-English stakeholder status updates | LLM |
| **Bridge** | Mirrors the room to the ops dashboard and relays the human's decision back into the room | deterministic (non-LLM) |

## Why Band is the whole point

- **Band is the only channel the agents have.** No orchestrator. Every handoff is a Band message with `@mentions`, and an agent acts only when mentioned — the workflow *emerges* from who addresses whom, exactly like a real on-call channel.
- **Humans and bots are first-class peers.** Two of the six participants (Detector, Bridge) are plain Python, indistinguishable room members alongside the reasoning agents.
- **Governance flows through the room too.** The human's Approve/Reject is injected back into Band as a message; the kill switch is itself a Band participant.
- **No shared memory.** Agents are stateless between turns — all shared context lives in the Band conversation.

## The human gate is real, not cosmetic

Remediation (`rollback` / `restart` / `scale`) is refused **at the action layer** until a human approves — and blocked attempts show on the timeline:

```
[ BLOCKED ]  rollback dpl-104   — awaiting human approval
[ HUMAN   ]  operator clicks APPROVE on the dashboard
[ OK      ]  rollback dpl-104   -> checkout healthy
```

No prompt can bypass it; it's enforced in code. That blocked-then-approved trace *is* the governance story.

## The dashboard

A FastAPI + polling ops console makes the invisible visible: a service **status board** (red → green), a **live timeline** of the Band conversation and blocked actions, the **APPROVE / REJECT** button, and **MTTR**.

## Architecture

```
                       ┌──────────────── Band room ────────────────┐
   metrics ─ Detector ─┤  @commander ⇄ @diagnostician ⇄ @remediator │
                       │        ⇅           ⇅            ⇅          │
                       │      @comms       Bridge (mirrors + relays)│
                       └────────────────────┬───────────────────────┘
                                            │  /timeline · /approval
                          ┌─────────────────▼──────────────────┐
                          │  FastAPI ops server                 │
                          │  • MockOps incident simulator       │
                          │  • action-layer approval gate       │
                          │  • dashboard (status, timeline,     │
                          │    APPROVE, MTTR)                    │
                          └─────────────────────────────────────┘
```

## Run it locally

Requires [uv](https://docs.astral.sh/uv/). Band agent credentials go in `app/agent_config.yaml` (see `app/agent_config.yaml.example`) and an OpenAI-compatible LLM key in `app/.env` (`OPENAI_BASE_URL` + `OPENAI_API_KEY`).

```bash
# 1. Launch the whole stack: 6 Band agents + ops server + dashboard
uv run --directory app python run_all.py

# 2. Trigger an incident (injects a bad deploy + raises the alert into the Band room)
uv run --directory app python demo_trigger.py            # or: memory_leak, dependency_outage

# 3. Open the dashboard and click APPROVE when the gate opens
#    http://localhost:8000/
```

Per-process logs land in `app/logs/*.log`. Scenarios: `bad_deploy` (rollback), `memory_leak` (restart), `dependency_outage` (scale).

## Tech stack

`Band SDK` · `Python` · `Featherless AI (Qwen2.5-14B, OpenAI-compatible)` · `FastAPI` · `vanilla HTML/JS dashboard` — each agent is a plain LLM tool-loop, no agent framework.

## Repo layout

```
app/
  warroom/        # the agents, ops server, Band seam, scenarios
    agent_main.py    band_io.py     server.py    bridge.py
    detector_main.py roles.py       tools.py     mockops.py    scenarios.py
  dashboard/      # status board + timeline + APPROVE button
  run_all.py      # launch everything   demo_trigger.py  # one-command incident
docs/             # design spec, plan, submission writeup, slide deck
```

Full write-up and slides: [`docs/SUBMISSION.md`](docs/SUBMISSION.md) · [`docs/WarRoom_Slides.pdf`](docs/WarRoom_Slides.pdf).

---

<sub>This repository was originally **`gpu-rental-mcp`**, an MCP server for renting vGPUs via Shadeform (TypeScript, under `src/`) — its README is preserved at [`docs/gpu-rental-mcp.md`](docs/gpu-rental-mcp.md). It was repurposed as the host for the War Room hackathon entry.</sub>
