from fastapi.testclient import TestClient
from warroom.server import app, OPS
from warroom import server as srv

def setup_function():
    OPS.reset()
    srv._incident.clear()
    srv._blocked_call.update(name=None, args=None)
    srv._remediation["approved"] = False
    srv._pending.update(pending=False, action=None, service=None)
    srv._pending.pop("last_decision", None)
    srv._log.clear()

def test_inject_and_status():
    c = TestClient(app)
    c.post("/inject", json={"scenario": "bad_deploy"})
    r = c.get("/status").json()
    checkout = [s for s in r["services"] if s["name"] == "checkout"][0]
    assert checkout["status"] == "degraded"

def test_read_action_not_gated():
    c = TestClient(app)
    c.post("/inject", json={"scenario": "bad_deploy"})
    out = c.post("/ops/get_metrics", json={"service": "checkout"}).json()
    assert out["error_rate"] == 0.42

def test_remediation_blocked_then_approved_heals():
    c = TestClient(app)
    c.post("/inject", json={"scenario": "bad_deploy"})
    # A gated action is refused until a human approves, and the block opens the gate.
    blocked = c.post("/ops/rollback", json={"deploy_id": "dpl-104"}).json()
    assert blocked.get("blocked") is True
    assert c.get("/approval/pending").json()["pending"] is True
    # On approval the server runs the held remediation itself -> checkout recovers.
    c.post("/approval/decide", json={"approved": True})
    checkout = [s for s in c.get("/status").json()["services"] if s["name"] == "checkout"][0]
    assert checkout["status"] == "healthy"

def test_pending_approval_lifecycle():
    c = TestClient(app)
    c.post("/approval/request", json={"action": "rollback", "service": "checkout"})
    assert c.get("/approval/pending").json()["pending"] is True
    c.post("/approval/decide", json={"approved": True})
    assert c.get("/approval/pending").json()["pending"] is False

def test_postmortem_ready_after_resolution():
    c = TestClient(app)
    assert c.get("/postmortem").json()["ready"] is False
    c.post("/inject", json={"scenario": "bad_deploy"})
    c.post("/ops/rollback", json={"deploy_id": "dpl-104"})   # blocked, opens gate
    c.post("/approval/decide", json={"approved": True})       # approve -> server heals
    pm = c.get("/postmortem").json()
    assert pm["ready"] is True
    assert pm["service"] == "checkout"
    assert "dpl-104" in pm["root_cause"]
    assert "Postmortem" in pm["markdown"]
