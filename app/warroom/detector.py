ERROR_RATE_WARN = 0.05
LATENCY_WARN = 500.0
CPU_WARN = 0.85

def detect(services: list[dict]) -> list[dict]:
    alerts = []
    for s in services:
        reasons = []
        if s["error_rate"] >= ERROR_RATE_WARN:
            reasons.append(f"error_rate={s['error_rate']:.0%}")
        if s["latency_ms"] >= LATENCY_WARN:
            reasons.append(f"latency_ms={s['latency_ms']:.0f}")
        if s["cpu"] >= CPU_WARN:
            reasons.append(f"cpu={s['cpu']:.0%}")
        if reasons:
            sev = "critical" if s["error_rate"] >= 0.2 or s["latency_ms"] >= 1000 else "warning"
            alerts.append({"service": s["name"], "severity": sev,
                           "reason": ", ".join(reasons)})
    return alerts

class Detector:
    """Stateful wrapper that fires each service at most once until it recovers."""
    def __init__(self):
        self._alerting: set[str] = set()

    def poll(self, services: list[dict]) -> list[dict]:
        current = detect(services)
        firing = {a["service"] for a in current}
        self._alerting &= firing
        new = [a for a in current if a["service"] not in self._alerting]
        self._alerting |= {a["service"] for a in new}
        return new
