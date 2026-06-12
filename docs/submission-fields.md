War Room is a multi-agent incident-response "team in a box." When a production service breaks, a band of specialized AI agents triages, diagnoses, and fixes the incident — coordinating entirely through Band, with a human holding the only key to anything destructive.

Six participants share one Band room. A Detector (non-LLM) watches metrics and raises the alert. The Commander opens the incident and delegates. The Diagnostician pulls live metrics, logs and deploys to pin the root cause. The Remediator proposes one fix and executes it — but only after approval. Comms posts plain-English stakeholder updates. A Bridge mirrors the room to an ops dashboard and relays the human's decision back into Band.

Our core bet: Band is the only channel the agents have. No orchestrator, no message bus, no shared memory. Every handoff is a Band message with @mentions, and an agent acts only when mentioned — so the workflow emerges from who addresses whom, exactly like a real on-call channel. Humans and bots are first-class peers: two of the six participants are plain Python, indistinguishable room members alongside the reasoning agents. Even governance flows through the room — the human's Approve/Reject is injected back into Band as a message to the Remediator.

The human gate is real, not cosmetic. We enforce it at the action layer: rollback, restart and scale are refused server-side until a human approves, and blocked attempts appear right on the timeline. A live dashboard shows service health flipping red to green, the Band conversation streaming in, the APPROVE button, and MTTR.

A full incident — detect, diagnose, block, approve, remediate, resolve — runs end-to-end in well under a minute.
