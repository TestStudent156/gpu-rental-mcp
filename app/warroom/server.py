import asyncio, json, time
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from warroom.mockops import MockOps
from warroom.tools import dispatch

class OpsState:
    def __init__(self): self.ops = MockOps()
    def reset(self): self.ops = MockOps()
OPS = OpsState()

app = FastAPI()
_events: "asyncio.Queue[dict]" = asyncio.Queue()
_log: list = []   # full event history (for observability / polling)
_pending = {"pending": False, "action": None, "service": None}
# Hard governance gate: remediation actions are refused until a human approves, regardless
# of what any agent tries. Armed by /approval/decide, consumed by one successful action,
# reset by a new incident. This makes the human-in-the-loop gate UNSKIPPABLE.
_remediation = {"approved": False}
GATED_ACTIONS = {"rollback", "restart", "scale"}

def emit(event: dict):
    _log.append(event)
    _events.put_nowait(event)

# --- Global multi-slot LLM gate --------------------------------------------------
# The hosted LLM plan has a fixed concurrency budget (Featherless: 4 units on Premium).
# Each model costs N units (1-unit <=15B, 2-unit 24-34B, 4-unit huge). LLM_SLOTS =
# plan_units // model_units = how many agent calls may run at once. Agents are separate
# processes, so they share the budget through this lease-based gate instead of colliding
# with 429s. Leases auto-expire so a crashed holder can never deadlock the room.
#   1-unit model (Qwen2.5-14B): LLM_SLOTS=4 -> all agents run in parallel.
#   4-unit model (DeepSeek-V4-Pro): LLM_SLOTS=1 -> strictly serial.
import os
LLM_SLOTS = int(os.environ.get("LLM_SLOTS", "4"))
LLM_LEASE = 90.0
_leases: "dict[str, float]" = {}   # token -> expiry timestamp
_lease_seq = {"n": 0}

@app.post("/llm/acquire")
async def llm_acquire():
    now = time.time()
    for k in [k for k, exp in _leases.items() if exp < now]:
        _leases.pop(k, None)
    if len(_leases) >= LLM_SLOTS:
        return {"granted": False}
    _lease_seq["n"] += 1
    tok = str(_lease_seq["n"])
    _leases[tok] = now + LLM_LEASE
    return {"granted": True, "token": tok}

@app.post("/llm/release")
async def llm_release(req: Request):
    body = await req.json()
    _leases.pop(str(body.get("token", "")), None)
    return {"ok": True}

@app.get("/timeline")
async def get_timeline():
    """Full event history — lets us observe the room without watching SSE live."""
    return {"events": _log}

@app.post("/inject")
async def inject(req: Request):
    body = await req.json()
    OPS.ops.inject(body["scenario"])
    _remediation["approved"] = False  # new incident -> remediation must be re-approved
    emit({"type": "incident_injected", "scenario": body["scenario"]})
    return {"ok": True}

@app.get("/status")
async def status():
    return {"services": OPS.ops.get_services()}

@app.post("/ops/{name}")
async def ops_action(name: str, req: Request):
    args = await req.json()
    # Enforce the human approval gate at the action layer: a remediation can never run until
    # a human has approved it, no matter what an agent attempts.
    if name in GATED_ACTIONS and not _remediation["approved"]:
        emit({"type": "action_blocked", "name": name, "args": args})
        return {"error": "BLOCKED: human approval required before remediation. Propose the "
                "fix and wait for an APPROVED message.", "blocked": True}
    out = dispatch(name, args, OPS.ops)
    emit({"type": "action", "name": name, "result": out})
    if name in GATED_ACTIONS:
        _remediation["approved"] = False  # one-shot: consume the approval
    return out

@app.post("/timeline")
async def timeline(req: Request):
    body = await req.json()
    emit({"type": "message", "sender": body["sender"], "content": body["content"]})
    return {"ok": True}

@app.post("/approval/request")
async def approval_request(req: Request):
    body = await req.json()
    _pending.update(pending=True, action=body["action"], service=body["service"])
    emit({"type": "approval_request", **body})
    return {"ok": True}

@app.get("/approval/pending")
async def approval_pending():
    return dict(_pending)

@app.post("/approval/decide")
async def approval_decide(req: Request):
    body = await req.json()
    decision = "APPROVED" if body["approved"] else "REJECTED"
    _pending.update(pending=False)
    _remediation["approved"] = bool(body["approved"])  # arm the action gate on approval
    emit({"type": "approval_decided", "decision": decision})
    _pending["last_decision"] = decision
    return {"ok": True, "decision": decision}

@app.get("/approval/last")
async def approval_last():
    return {"decision": _pending.pop("last_decision", None)}

@app.get("/events")
async def events():
    async def gen():
        while True:
            ev = await _events.get()
            yield f"data: {json.dumps(ev)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")

_DASH = Path(__file__).resolve().parents[1] / "dashboard"
@app.get("/")
async def index():
    return FileResponse(_DASH / "index.html")
app.mount("/static", StaticFiles(directory=_DASH), name="static")
