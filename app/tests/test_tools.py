from warroom.mockops import MockOps
from warroom.tools import TOOL_SCHEMAS, dispatch, tools_for

def test_schemas_have_names_and_input_schema():
    for t in TOOL_SCHEMAS:
        assert "name" in t and "input_schema" in t and "description" in t

def test_dispatch_get_metrics():
    ops = MockOps(); ops.inject("bad_deploy")
    out = dispatch("get_metrics", {"service": "checkout"}, ops)
    assert out["error_rate"] > 0.2

def test_dispatch_rollback_heals():
    ops = MockOps(); ops.inject("bad_deploy")
    out = dispatch("rollback", {"deploy_id": "dpl-104"}, ops)
    assert out["ok"] is True

def test_tools_for_diagnostician_is_readonly():
    names = {t["name"] for t in tools_for("diagnostician")}
    assert "get_metrics" in names and "query_logs" in names
    assert "rollback" not in names

def test_tools_for_remediator_can_act():
    names = {t["name"] for t in tools_for("remediator")}
    assert {"rollback", "restart", "scale"} <= names
