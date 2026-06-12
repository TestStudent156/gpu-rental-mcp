# War Room — Multi-Agent Incident Response on Band

**Hackathon:** Band of Agents (lablab.ai) · June 12–19, 2026 · online · $10,000+ prize pool
**Status:** Design approved 2026-06-12
**Working title:** War Room

---

## 1. One-line concept

A band of AI agents that resolves live infrastructure incidents in a simulated cloud/SaaS
environment, coordinating **entirely through Band**, with a human approval gate on remediation
and a lightweight ops dashboard for the enterprise view.

## 2. Why this fits the hackathon

The hackathon has exactly two judging criteria:

1. **Application of Technology** — how effectively the solution uses **Band as the coordination
   layer** between multiple specialized agents (clear handoffs, shared context, role
   specialization, task state, governance).
2. **Clarity of presentation** — how legibly the multi-agent workflow is demonstrated.

Incident response is inherently a "war room": multiple specialists convene, talk full-duplex,
hand off, and a governance gate controls who may execute a fix. This maps onto Band's
"agents talk like teammates in a shared room" pitch one-to-one, and the dashboard makes the
enterprise value legible in a single screen.

## 3. Architecture

N independent Claude agents, each its own process, all joined to a single **Band room**.
Every handoff, hypothesis, decision, and approval flows through Band — **no agent ever calls
another directly, and there is no separate orchestrator. Band IS the orchestration.**

A FastAPI backend plays three supporting (non-coordinating) roles:

- **Simulates the infra world** ("MockOps") that agents inspect and act on via tools.
- **Bridges Band → dashboard**: subscribes to the Band room and forwards events to the
  dashboard over SSE.
- **Bridges human → Band**: injects the human APPROVE/REJECT decision back into the room as a
  governance message.

```
  Detector ──alert──▶ ┌──────────────── BAND ROOM ────────────────┐
                      │  Commander  Diagnostician  Remediator      │
                      │             Comms        (Specialist*)     │
                      └───────▲───────────────────────────┬───────┘
                              │ governance msg            │ room events
   Human (dashboard) ─APPROVE─┘                           ▼
                                              FastAPI bridge ──SSE──▶ Dashboard
   Agents ◀──tools──▶ MockOps sim env (metrics / logs / deploys / actions)
   * Specialist = stretch goal (dynamic recruitment)
```

## 4. The band (agents)

Four agents — exceeds the ≥3 requirement; each clearly specialized.

| Agent | Role | Model |
|---|---|---|
| **Commander** | Incident Commander — opens the incident, assigns work, tracks task state, requests human approval, declares resolution | `claude-opus-4-8` |
| **Diagnostician** | Pulls logs/metrics/deploy history, forms a root-cause hypothesis, reports to the room | `claude-sonnet-4-6` |
| **Remediator** | Proposes a concrete fix (rollback / restart / scale) with risk; execution **gated** behind human approval | `claude-sonnet-4-6` |
| **Comms** | Drafts stakeholder status updates (investigating → identified → monitoring → resolved), posts to the timeline | `claude-haiku-4-5` |

**Stretch (Approach 3 — dynamic recruitment):** Commander discovers and **recruits** a DB or
Network Specialist on-demand based on incident type, showcasing Band's agent-discovery feature.

Each agent is built on the **plain Anthropic SDK** (no LangGraph/CrewAI) — adding another
orchestration framework would muddy the "Band is the orchestrator" story. An agent is a loop:
system prompt (role) + tool set (MockOps subset) + Band room connection.

## 5. Simulated environment — "MockOps"

A small Python module exposing tools the agents call via function calling:

- **Service registry** — services + health status.
- **Metrics** — latency / error-rate / CPU time-series that an injected incident perturbs.
- **Logs** — queryable.
- **Deploy history** — recent deploys (the usual culprit).
- **Action API** — `rollback(deploy)`, `restart(service)`, `scale(service)` → flip the world
  back to healthy.
- **Incident injector** — scripted scenarios: *bad deploy spikes errors*, *memory leak*,
  *dependency outage*.

A **non-LLM Detector** watches the metrics and drops an alert into the Band room. Keeping
detection deterministic makes the demo reliable and reproducible.

## 6. Data flow (golden path)

1. Incident injected → metrics degrade → Detector posts an alert to the Band room.
2. **Commander** opens the incident, assigns Diagnostician + tells Comms to post "investigating."
3. **Diagnostician** queries logs/metrics/deploys → posts root-cause hypothesis to the room.
4. **Commander** asks **Remediator** to propose a fix → Remediator posts action + risk.
5. Commander requests approval → **dashboard shows APPROVE / REJECT**.
6. Human approves → approval re-enters the Band room as a governance message → Remediator
   executes against the sim env → metrics recover.
7. **Comms** posts "resolved," Commander declares resolution. Band's audit trail = the full
   incident record. *(Stretch: Commander triggers an auto-postmortem.)*

## 7. Dashboard (enterprise view)

Single screen, fed **entirely by Band room events via SSE** so Band stays the single source
of truth:

- **Service status board** — red → green tiles.
- **Live incident timeline** — events as they happen.
- **Current owner / active agent.**
- **APPROVE / REJECT button** — appears only when remediation is pending.
- **MTTR clock** — time since incident start.

## 8. Tech stack

- Python 3.11+
- **Band Python SDK** (docs: `docs.thenvoi.com`)
- **Anthropic SDK** (`claude-opus-4-8`, `claude-sonnet-4-6`, `claude-haiku-4-5`)
- **FastAPI** — sim env API + Band↔dashboard bridge + SSE
- Minimal HTML/JS frontend (no framework)
- One `run` script (or docker-compose) launches all agents + backend + dashboard.

## 9. Testing

- A **scenario runner** that injects an incident and asserts the band reaches "resolved."
- Manual demo runs.
- Focus: **one rock-solid golden scenario** for the demo video, two backups.

## 10. Plan (June 12 → submit June 19)

- **Day 1 (today):** Band SDK spike — two Claude agents talking in a room; scaffold repo; read
  `docs.thenvoi.com`. **Validate the four Band assumptions (§11).**
- **Day 2:** Sim env + Detector → alert into room.
- **Day 3:** Commander + Diagnostician → investigate → root-cause through Band.
- **Day 4:** Remediator + approval gate + Comms → end-to-end golden path resolves.
- **Day 5:** Dashboard wired to Band events.
- **Day 6:** Polish + stretch (dynamic recruitment / postmortem) + backup scenarios.
- **Day 7:** Record demo, write submission, rehearse. Buffer.

## 11. Primary risk — Band SDK validation (Day 1 spike)

Everything hinges on the Band Python SDK supporting all four of:

1. Connecting an **Anthropic agent** to Band.
2. A **multi-agent room** (≥4 participants).
3. **Programmatic subscription** to room messages (for the dashboard bridge).
4. Injecting a **human/governance message** into the room (the approval).

If any is missing, adapt the design early (e.g. approval via a side channel that still
records into Band's audit trail). Confirm before building anything else.

## 12. Out of scope (YAGNI)

- Real cloud provider integration.
- Authentication / multi-tenant.
- Persistent database (in-memory sim state is fine for the demo).
- More than three incident scenarios.
- Anything not visible in the 3–5 minute demo video.
