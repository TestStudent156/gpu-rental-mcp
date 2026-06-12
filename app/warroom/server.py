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

def emit(event: dict):
    _log.append(event)
    _events.put_nowait(event)

# --- Global single-slot LLM gate -------------------------------------------------
# The hosted LLM plan allows only one concurrent request (DeepSeek-V4-Pro = 4 units,
# plan limit = 4). Agents are separate processes, so they serialize their LLM calls
# through this lease-based gate instead of colliding with 429s. The lease auto-expires
# so a crashed holder can never deadlock the room.
_llm_gate = {"held": False, "since": 0.0}
LLM_LEASE = 90.0

@app.post("/llm/acquire")
async def llm_acquire():
    now = time.time()
    if _llm_gate["held"] and (now - _llm_gate["since"]) < LLM_LEASE:
        return {"granted": False}
    _llm_gate["held"] = True
    _llm_gate["since"] = now
    return {"granted": True}

@app.post("/llm/release")
async def llm_release():
    _llm_gate["held"] = False
    return {"ok": True}

@app.get("/timeline")
async def get_timeline():
    """Full event history — lets us observe the room without watching SSE live."""
    return {"events": _log}

@app.post("/inject")
async def inject(req: Request):
    body = await req.json()
    OPS.ops.inject(body["scenario"])
    emit({"type": "incident_injected", "scenario": body["scenario"]})
    return {"ok": True}

@app.get("/status")
async def status():
    return {"services": OPS.ops.get_services()}

@app.post("/ops/{name}")
async def ops_action(name: str, req: Request):
    args = await req.json()
    out = dispatch(name, args, OPS.ops)
    emit({"type": "action", "name": name, "result": out})
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
