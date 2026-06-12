from warroom.mockops import MockOps

def test_seed_is_healthy():
    ops = MockOps()
    services = {s["name"]: s for s in ops.get_services()}
    assert "checkout" in services
    assert services["checkout"]["status"] == "healthy"
    assert services["checkout"]["error_rate"] < 0.01

def test_metrics_returns_known_fields():
    ops = MockOps()
    m = ops.get_metrics("checkout")
    assert set(m) >= {"error_rate", "latency_ms", "cpu"}

def test_unknown_service_raises():
    ops = MockOps()
    import pytest
    with pytest.raises(KeyError):
        ops.get_metrics("nope")
