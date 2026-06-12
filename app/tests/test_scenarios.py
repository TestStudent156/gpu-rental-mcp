from warroom.mockops import MockOps
from warroom.scenarios import SCENARIOS

def test_bad_deploy_degrades_checkout_and_marks_bad_deploy():
    ops = MockOps()
    ops.inject("bad_deploy")
    m = ops.get_metrics("checkout")
    assert m["error_rate"] > 0.2
    assert ops.get_services_by_status("degraded")
    bad = [d for d in ops.get_deploys("checkout") if d["is_bad"]]
    assert len(bad) == 1

def test_rollback_correct_deploy_heals():
    ops = MockOps()
    ops.inject("bad_deploy")
    bad_id = [d for d in ops.get_deploys("checkout") if d["is_bad"]][0]["id"]
    res = ops.rollback(bad_id)
    assert res["ok"] is True
    assert ops.get_metrics("checkout")["error_rate"] < 0.01
    assert ops.get_services_by_status("degraded") == []

def test_rollback_wrong_deploy_does_not_heal():
    ops = MockOps()
    ops.inject("bad_deploy")
    res = ops.rollback("dpl-102")
    assert res["ok"] is False
    assert ops.get_metrics("checkout")["error_rate"] > 0.2

def test_memory_leak_heals_on_restart():
    ops = MockOps()
    ops.inject("memory_leak")
    assert ops.get_metrics("payments")["cpu"] > 0.85
    ops.restart("payments")
    assert ops.get_metrics("payments")["cpu"] < 0.4

def test_dependency_outage_heals_on_scale():
    ops = MockOps()
    ops.inject("dependency_outage")
    assert ops.get_metrics("catalog")["latency_ms"] > 800
    ops.scale("catalog", replicas=4)
    assert ops.get_metrics("catalog")["latency_ms"] < 100

def test_all_scenarios_have_required_fields():
    for name, sc in SCENARIOS.items():
        assert {"service", "remedy", "logs"} <= set(sc)
        assert sc["remedy"]["action"] in {"rollback", "restart", "scale"}
