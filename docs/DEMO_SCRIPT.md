# War Room — 60-second demo video script

**Goal:** in one minute, prove the two judging criteria — (1) Band is the real coordination
layer, (2) the story reads at a glance — and land the one unforgettable beat: a destructive
action **blocked**, a human **approving**, and the system **healing**.

**Recommended layout:** split screen — **left:** the Band room (app.band.ai) so judges see the
agents actually talking; **right:** the War Room dashboard (`localhost:8000`). If a split is
fiddly, just record the dashboard — its live timeline mirrors the Band conversation.

**Tip:** do a dry run first so the cascade is warm; keep your cursor near the **APPROVE** button.

---

| Time | On screen | Voiceover (read at a calm pace) |
|---|---|---|
| **0:00–0:07** | Dashboard: 4 services all **green**, empty timeline. | "This is War Room — an on-call team made of AI agents. Six of them share one Band room, and they're about to handle a production incident together." |
| **0:07–0:15** | Run `inject bad_deploy` + `kickoff`. Checkout flips **red** (error rate 42%). A 🚨 alert appears in the Band room. | "A bad deploy just took down checkout. The Detector — a Band participant — raises the alert." |
| **0:15–0:27** | Band room streams: Commander → @diagnostician / @comms; Diagnostician replies. Dashboard timeline mirrors it live. | "The Commander opens the incident and delegates — entirely through Band. No orchestrator, no central script. The Diagnostician pulls the logs and metrics…" |
| **0:27–0:35** | Diagnostician's message highlighting **dpl-104**. | "…and pins the root cause: deploy dpl-104 introduced a null-pointer in the pricing service." |
| **0:35–0:46** | Timeline shows **`action_blocked: rollback dpl-104`** (red), then **`APPROVAL REQUESTED: rollback dpl-104 on checkout`**. *(Hover/zoom on the blocked line.)* | "Now the important part. The Remediator tries to roll back — and the system **blocks it**. No agent can touch production until a human says yes. That gate is enforced in code, not just a prompt." |
| **0:46–0:53** | Cursor moves to **APPROVE** and clicks. Bridge posts `APPROVED` into the Band room. | "That's me — the human in the loop. One click. The approval goes *back into the Band room* as a message to the Remediator." |
| **0:53–0:60** | `action: rollback dpl-104 → ok`. Checkout flips **green**. Commander posts **INCIDENT RESOLVED**. MTTR ticks up. | "The rollback runs, checkout recovers, and the Commander closes it out. A full incident — triaged, diagnosed, and fixed by a band of agents, with a human holding the only key." |

**End card (hold 2s):**
> **War Room** — a band of agents that runs your incident response.
> Coordinated entirely through **Band**.

---

## Beat checklist (don't end the recording without these)
- [ ] A service visibly goes **red → green**
- [ ] The **Band room** shows agents @mentioning each other (not just the dashboard)
- [ ] The **`action_blocked`** line is on screen long enough to read
- [ ] The **human click** on APPROVE is visible
- [ ] **INCIDENT RESOLVED** + MTTR at the end

## If you want a tighter 30s cut
Keep 0:00–0:07 (hook), 0:07–0:15 (incident), 0:35–0:53 (blocked → approve), 0:53–0:60
(resolved). Drop the diagnosis detail. The blocked-then-approved beat is the one that must survive.
