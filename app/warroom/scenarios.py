"""Each scenario degrades one service and defines the single correct remedy."""
SCENARIOS = {
    "bad_deploy": {
        "service": "checkout",
        "degrade": {"error_rate": 0.42, "latency_ms": 220.0, "status": "degraded"},
        "remedy": {"action": "rollback", "target": "checkout"},
        "logs": [
            "ERROR checkout: 500 from /charge after deploy dpl-104 v1.5.0",
            "ERROR checkout: NullPointer in PricingService.apply()",
            "INFO  checkout: deploy dpl-104 v1.5.0 rolled out 3m ago",
        ],
    },
    "memory_leak": {
        "service": "payments",
        "degrade": {"cpu": 0.94, "latency_ms": 600.0, "status": "degraded"},
        "remedy": {"action": "restart", "target": "payments"},
        "logs": [
            "WARN  payments: heap usage 94% and climbing",
            "WARN  payments: GC pause 1.2s",
        ],
    },
    "dependency_outage": {
        "service": "catalog",
        "degrade": {"latency_ms": 1500.0, "error_rate": 0.15, "status": "degraded"},
        "remedy": {"action": "scale", "target": "catalog"},
        "logs": [
            "ERROR catalog: upstream search-db timeout (3 of 4 replicas saturated)",
            "WARN  catalog: request queue depth 480",
        ],
    },
}
