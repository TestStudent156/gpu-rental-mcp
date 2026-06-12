from fastapi.testclient import TestClient
from warroom.server import app, OPS

def setup_function():
    OPS.reset()

def test_inject_and_status():
    c = TestClient(app)
    c.post("/inject", json={"scenario": "bad_deploy"})
    r = c.get("/status").json()
    checkout = [s for s in r["services"] if s["name"] == "checkout"][0]
    assert checkout["status"] == "degraded"

def test_ops_action_endpoint():
    c = TestClient(app)
    c.post("/inject", json={"scenario": "bad_deploy"})
    out = c.post("/ops/rollback", json={"deploy_id": "dpl-104"}).json()
    assert out["ok"] is True

def test_pending_approval_lifecycle():
    c = TestClient(app)
    c.post("/approval/request", json={"action": "rollback", "service": "checkout"})
    assert c.get("/approval/pending").json()["pending"] is True
    c.post("/approval/decide", json={"approved": True})
    assert c.get("/approval/pending").json()["pending"] is False
