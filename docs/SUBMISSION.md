# War Room — a band of AI agents that runs your incident response

**Tagline:** When production breaks, a team of specialized AI agents triages, diagnoses, and fixes the incident — coordinating *entirely* through Band — while a human holds the only key to the remediation.

**Hackathon:** lablab.ai · Band of Agents
**Team:** pokeyoke

---

## The one-liner

War Room is a multi-agent incident-response "team in a box." A detector raises an alert, an Incident Commander opens the case, a Diagnostician finds the root cause from live telemetry, a Remediator proposes a fix — and nothing touches production until a human clicks **Approve**. Every agent talks to every other agent through **one Band room**. There is no hidden orchestrator, no message bus, no shared database. **Band is the nervous system.**

---

## The problem

Real incident response is a coordination problem, not a model problem. When a service degrades at 3 a.m., the hard part isn't any single decision — it's the handoffs: who investigates, who's allowed to act, who tells stakeholders, and who makes sure a bot doesn't roll back the wrong thing. Most "AI agent" demos hard-wire these handoffs into a central orchestrator. That orchestrator *is* the product, and the agents are just function calls.

We wanted the opposite: agents that are genuinely independent participants in a shared conversation, coordinating the way a real on-call team does — by talking in a channel — with a human firmly in the loop on anything destructive.

## The solution

Six participants share a single Band room:

| Agent | Role | Powered by |
|---|---|---|
| **Detector** | Watches service metrics; raises the alert that starts everything | deterministic (non-LLM) |
| **Commander** | Opens the incident, delegates, requests human approval, declares resolved | LLM, coordinate-only |
| **Diagnostician** | Pulls metrics / logs / deploys, pins the root cause | LLM + read tools |
| **Remediator** | Proposes one concrete fix; executes it *only after approval* | LLM + action tools |
| **Comms** | Posts plain-English stakeholder status updates | LLM |
| **Bridge** | Mirrors the room to the ops dashboard and relays the human's approval decision back into the room | deterministic (non-LLM) |

A full run, coordinated 100% through Band:

```
Detector  → @commander  🚨 ALERT checkout error_rate 42%
Commander → @diagnostician investigate checkout · @comms post an update
Diagnostician → @commander root cause: deploy dpl-104 (v1.5.0) NullPointer in PricingService
Commander → @remediator propose a fix
Remediator → tries rollback → ❌ BLOCKED (human approval required) → proposes "rollback dpl-104 on checkout", waits
Commander → APPROVAL REQUESTED: rollback dpl-104 on checkout
        ── human clicks APPROVE ──
Bridge    → @remediator APPROVED — execute rollback dpl-104 on checkout
Remediator → rollback dpl-104 ✅ → checkout healthy → @comms
Commander → INCIDENT RESOLVED
```

End-to-end in well under a minute, with the human gate in the middle.

---

## How we used Band (our core technical bet)

**Band is the only channel agents have.** There is no orchestrator process. Every handoff is a real Band message with `@mention`s, and an agent acts only when it is mentioned. This gave us properties that are hard to fake:

- **Mention-driven turn-taking.** The "workflow" is emergent from who addresses whom — exactly how a human channel works. Change the prompt, change the org chart; no orchestration code to rewrite.
- **Humans and bots are first-class peers.** Two of our six participants (Detector, Bridge) are plain Python, not LLMs. Band carries deterministic actors and reasoning agents over the *same* interface, so a metrics watcher and a GPT-class agent are indistinguishable room members.
- **Governance flows through the room too.** The human's Approve/Reject doesn't bypass the agents — the Bridge injects the decision back into Band as a message addressed to the Remediator. The kill switch is itself a Band participant.
- **No shared memory.** Agents are stateless between turns; all shared context lives in the Band conversation. This forced a clean design and proved Band can carry the full coordination state.

We deliberately treated Band not as a chat UI but as the **coordination substrate** — the thing that makes six independent processes behave like one team.

## The human-in-the-loop gate (and why it's real)

A demo where an agent "asks for approval" is only convincing if approval is actually enforced. So we enforce it at the **action layer, not the prompt layer**: the ops backend *refuses* every remediation (`rollback`/`restart`/`scale`) until a human approves — and it logs the refusal. If the Remediator jumps the gun, you literally see:

```
action_blocked: rollback dpl-104
action_blocked: rollback dpl-104
[human approves]
action: rollback dpl-104 → ok
```

The gate is **unskippable regardless of what any model does**. That blocked-then-approved trace, visible right on the timeline, *is* the governance story.

## The dashboard

A lightweight FastAPI + SSE ops console makes the invisible visible:

- **Service status board** — health, error rate, latency per service, flipping red → green as the incident resolves
- **Live timeline** — the Band conversation streaming in real time, including blocked-action events
- **APPROVE / REJECT** — the one human action, front and center
- **MTTR** — time from alert to resolved

The whole story reads at a glance, which matters as much as the agents themselves.

---

## Architecture

```
                         ┌──────────────── Band room ────────────────┐
   metrics ── Detector ──┤  @commander ⇄ @diagnostician ⇄ @remediator │
                         │        ⇅            ⇅            ⇅         │
                         │      @comms        Bridge  (mirrors + relays)
                         └─────────────────────┬──────────────────────┘
                                               │  /timeline · /approval
                              ┌────────────────▼─────────────────┐
                              │  FastAPI ops server               │
                              │  • MockOps incident simulator     │
                              │  • action-layer approval gate     │
                              │  • SSE → dashboard (status,        │
                              │    timeline, APPROVE, MTTR)        │
                              └───────────────────────────────────┘
```

- **Agents:** one process each, plain LLM tool-loop (no agent framework), connected to Band via the Band Python SDK with a custom `SimpleAdapter`.
- **Reasoning model:** Qwen2.5-14B-Instruct served by **Featherless AI** (OpenAI-compatible). A 1-unit model lets all four reasoning agents run concurrently within the plan's budget, so a full incident resolves in seconds.
- **Ops backend:** FastAPI + a deterministic in-memory `MockOps` that models services, metrics, deploys, and the three remediation actions — fully reproducible for a clean demo.

## Tech stack

`Band SDK` · `Python` · `Featherless AI (Qwen2.5-14B-Instruct, OpenAI-compatible API)` · `FastAPI` · `Server-Sent Events` · `vanilla HTML/JS dashboard`

---

## Challenges we solved

- **Band as the *only* bus.** Messages reach only `@mentioned` agents, so we built a directory that resolves roles → handles, a "CC the bridge" rule so the dashboard sees everything, and mention-gated turn-taking. We also added a stale-message filter + id-dedup so room history never re-triggers a cascade.
- **Stateless agents, stateful incident.** Because nothing persists between turns, the approval relay echoes the *exact* approved action back into the room so the Remediator executes precisely what was authorized.
- **Small-model discipline.** Driving a 14B model reliably meant stripping the Commander's tools (coordinate-only), making Comms a terminal sink to kill a chatter loop, and — crucially — enforcing the approval gate in code rather than trusting the prompt.

## What's next

- **Dynamic recruitment** — the Commander pulls a specialist (DB, network) into the room when the incident type calls for it.
- **Auto-postmortem** — a seventh agent writes the incident report from the Band transcript once resolved.
- **Real integrations** — swap `MockOps` for live observability + a real change-management approval.

## Try it

```bash
uv run --directory app python run_all.py          # 6 Band agents + ops server + dashboard
curl -X POST localhost:8000/inject -d '{"scenario":"bad_deploy"}'
uv run --directory app python kickoff.py           # raise the alert into the Band room
# open http://localhost:8000/ and click APPROVE when the gate opens
```

Scenarios included: `bad_deploy` (rollback), `memory_leak` (restart), `dependency_outage` (scale).

---

**War Room shows what Band is *for*: not a chat window bolted onto agents, but the coordination layer that lets a team of them — and a human — run a real operation together.**
