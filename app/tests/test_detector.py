from warroom.mockops import MockOps
from warroom.detector import detect, Detector

def test_no_alert_when_healthy():
    ops = MockOps()
    assert detect(ops.get_services()) == []

def test_alert_on_high_error_rate():
    ops = MockOps()
    ops.inject("bad_deploy")
    alerts = detect(ops.get_services())
    assert len(alerts) == 1
    a = alerts[0]
    assert a["service"] == "checkout"
    assert a["severity"] in {"warning", "critical"}
    assert "error_rate" in a["reason"]

def test_detector_fires_each_service_once():
    ops = MockOps()
    ops.inject("bad_deploy")
    det = Detector()
    first = det.poll(ops.get_services())
    second = det.poll(ops.get_services())
    assert len(first) == 1
    assert second == []
