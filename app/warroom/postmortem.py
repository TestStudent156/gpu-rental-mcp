"""Deterministic auto-postmortem: turns a resolved incident + its event log into a report.

No LLM involved — it reads the timeline the agents produced, so it is always available the
moment the incident is resolved.
"""
from datetime import datetime, timezone

_GATED = {"rollback", "restart", "scale"}


def _hms(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%H:%M:%S")


def _dur(seconds):
    seconds = int(round(max(0.0, seconds)))
    m, s = divmod(seconds, 60)
    return f"{m}m {s:02d}s" if m else f"{s}s"


def build(incident, log):
    """incident: dict with scenario/service/severity/cause/remedy_desc/started_ts/resolved_ts.
    Returns {ready: False} until the incident is resolved, else the full report."""
    if not incident or not incident.get("resolved_ts") or not incident.get("started_ts"):
        return {"ready": False}

    start, end = incident["started_ts"], incident["resolved_ts"]
    mttr = max(0.0, end - start)

    rows = []
    for ev in log:
        t = ev.get("ts", start)
        rel = f"+{_dur(t - start)}"
        typ = ev.get("type")
        if typ == "incident_injected":
            rows.append((rel, f"Incident detected ({ev.get('scenario')})"))
        elif typ == "action_blocked":
            rows.append((rel, f"Remediation '{ev.get('name')}' blocked — awaiting human approval"))
        elif typ == "approval_request":
            rows.append((rel, f"Approval requested: {ev.get('action')}"))
        elif typ == "approval_decided":
            rows.append((rel, f"Human {ev.get('decision')}"))
        elif typ == "action" and ev.get("name") in _GATED:
            rows.append((rel, f"Remediation applied: {ev.get('name')}"))
    timeline = "\n".join(f"- `{rel:>7}`  {txt}" for rel, txt in rows) or "- (no events captured)"

    action = incident.get("remedy_desc") or incident.get("action") or "remediation applied"
    markdown = (
        f"# Incident Postmortem — {incident['service']}\n\n"
        f"**Severity:** {incident.get('severity', '-')}  ·  "
        f"**Detected:** {_hms(start)} UTC  ·  **Resolved:** {_hms(end)} UTC  ·  "
        f"**MTTR:** {_dur(mttr)}\n\n"
        f"**Root cause:** {incident.get('cause', '-')}\n\n"
        f"**Action taken:** {action} — executed only after **human approval**.\n\n"
        f"## Timeline\n{timeline}\n\n"
        f"## Follow-ups\n"
        f"- [ ] Add a regression test reproducing the root cause.\n"
        f"- [ ] Review the guardrail that let this reach production.\n"
    )

    return {
        "ready": True,
        "service": incident["service"],
        "severity": incident.get("severity"),
        "mttr": _dur(mttr),
        "mttr_seconds": round(mttr, 1),
        "detected": _hms(start),
        "resolved": _hms(end),
        "root_cause": incident.get("cause"),
        "action": action,
        "markdown": markdown,
    }
