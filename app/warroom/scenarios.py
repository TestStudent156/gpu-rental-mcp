"""Each scenario degrades one service and defines the single correct remedy.

`cause` and `remedy_desc` are human-readable strings used by the auto-postmortem.
"""
SCENARIOS = {
    "bad_deploy": {
        "service": "checkout",
        "severity": "critical",
        "degrade": {"error_rate": 0.42, "latency_ms": 220.0, "status": "degraded"},
        "remedy": {"action": "rollback", "target": "checkout"},
        "cause": "Deploy dpl-104 (v1.5.0) introduced a NullPointerException in "
                 "PricingService.apply(), causing 500s on /charge.",
        "remedy_desc": "Rolled back deploy dpl-104 to the last-known-good version.",
        "logs": [
            "ERROR checkout: 500 from /charge after deploy dpl-104 v1.5.0",
            "ERROR checkout: NullPointer in PricingService.apply()",
            "INFO  checkout: deploy dpl-104 v1.5.0 rolled out 3m ago",
        ],
    },
    "memory_leak": {
        "service": "payments",
        "severity": "critical",
        "degrade": {"cpu": 0.94, "latency_ms": 600.0, "status": "degraded"},
        "remedy": {"action": "restart", "target": "payments"},
        "cause": "A memory leak in payments drove heap usage to 94% with multi-second "
                 "GC pauses, spiking latency.",
        "remedy_desc": "Restarted the payments service to reclaim heap.",
        "logs": [
            "WARN  payments: heap usage 94% and climbing",
            "WARN  payments: GC pause 1.2s",
        ],
    },
    "dependency_outage": {
        "service": "catalog",
        "severity": "warning",
        "degrade": {"latency_ms": 1500.0, "error_rate": 0.15, "status": "degraded"},
        "remedy": {"action": "scale", "target": "catalog"},
        "cause": "Upstream search-db saturation (3 of 4 replicas) backed up the catalog "
                 "request queue, spiking latency to 1.5s.",
        "remedy_desc": "Scaled catalog out to absorb the queue while the dependency recovered.",
        "logs": [
            "ERROR catalog: upstream search-db timeout (3 of 4 replicas saturated)",
            "WARN  catalog: request queue depth 480",
        ],
    },
}
