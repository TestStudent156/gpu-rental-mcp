from dataclasses import dataclass, field, asdict
from copy import deepcopy

@dataclass
class Service:
    name: str
    status: str = "healthy"          # healthy | degraded | down
    error_rate: float = 0.002
    latency_ms: float = 40.0
    cpu: float = 0.25

@dataclass
class Deploy:
    id: str
    service: str
    version: str
    ts: str
    is_bad: bool = False

_SEED_SERVICES = ["checkout", "payments", "catalog", "auth"]
_SEED_DEPLOYS = [
    Deploy("dpl-101", "checkout", "v1.4.0", "2026-06-12T08:00:00Z"),
    Deploy("dpl-102", "payments", "v2.1.0", "2026-06-12T08:30:00Z"),
    Deploy("dpl-103", "catalog",  "v3.0.0", "2026-06-12T09:00:00Z"),
]

class MockOps:
    def __init__(self):
        self.services: dict[str, Service] = {n: Service(n) for n in _SEED_SERVICES}
        self.deploys: list[Deploy] = deepcopy(_SEED_DEPLOYS)
        self.logs: dict[str, list[str]] = {n: [] for n in _SEED_SERVICES}
        self._active_scenario = None

    def _svc(self, name: str) -> Service:
        if name not in self.services:
            raise KeyError(name)
        return self.services[name]

    def get_services(self) -> list[dict]:
        return [asdict(s) for s in self.services.values()]

    def get_metrics(self, name: str) -> dict:
        s = self._svc(name)
        return {"error_rate": s.error_rate, "latency_ms": s.latency_ms, "cpu": s.cpu}

    def query_logs(self, name: str, level: str | None = None) -> list[str]:
        lines = self.logs.get(name, [])
        if level:
            lines = [l for l in lines if level.upper() in l]
        return list(lines)

    def get_deploys(self, name: str | None = None) -> list[dict]:
        return [asdict(d) for d in self.deploys if name is None or d.service == name]

    def get_services_by_status(self, status: str) -> list[str]:
        return [n for n, s in self.services.items() if s.status == status]

    def inject(self, scenario_name: str):
        from warroom.scenarios import SCENARIOS
        sc = SCENARIOS[scenario_name]
        self._active_scenario = scenario_name
        s = self._svc(sc["service"])
        for k, v in sc["degrade"].items():
            setattr(s, k, v)
        self.logs[sc["service"]].extend(sc["logs"])
        if sc["remedy"]["action"] == "rollback":
            bad = Deploy("dpl-104", sc["service"], "v1.5.0",
                         "2026-06-12T09:30:00Z", is_bad=True)
            self.deploys.append(bad)

    def _heal(self, name: str):
        fresh = Service(name)
        s = self._svc(name)
        s.status, s.error_rate, s.latency_ms, s.cpu = (
            fresh.status, fresh.error_rate, fresh.latency_ms, fresh.cpu)

    def _correct(self, action: str, target: str) -> bool:
        from warroom.scenarios import SCENARIOS
        if not self._active_scenario:
            return False
        r = SCENARIOS[self._active_scenario]["remedy"]
        return r["action"] == action and r["target"] == target

    def rollback(self, deploy_id: str) -> dict:
        match = [d for d in self.deploys if d.id == deploy_id]
        if match and match[0].is_bad and self._correct("rollback", match[0].service):
            self._heal(match[0].service)
            match[0].is_bad = False
            self._active_scenario = None
            return {"ok": True, "action": "rollback", "deploy_id": deploy_id}
        return {"ok": False, "action": "rollback", "deploy_id": deploy_id,
                "reason": "deploy not the faulty one"}

    def restart(self, name: str) -> dict:
        ok = self._correct("restart", name)
        if ok:
            self._heal(name); self._active_scenario = None
        return {"ok": ok, "action": "restart", "service": name}

    def scale(self, name: str, replicas: int = 4) -> dict:
        ok = self._correct("scale", name)
        if ok:
            self._heal(name); self._active_scenario = None
        return {"ok": ok, "action": "scale", "service": name, "replicas": replicas}
