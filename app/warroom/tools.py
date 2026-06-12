"""Anthropic tool schemas wrapping MockOps, plus per-role tool subsets."""

TOOL_SCHEMAS = [
    {"name": "get_services", "description": "List all services and their health.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_metrics", "description": "Get error_rate/latency/cpu for a service.",
     "input_schema": {"type": "object",
        "properties": {"service": {"type": "string"}}, "required": ["service"]}},
    {"name": "query_logs", "description": "Get recent log lines for a service.",
     "input_schema": {"type": "object",
        "properties": {"service": {"type": "string"},
                       "level": {"type": "string"}}, "required": ["service"]}},
    {"name": "get_deploys", "description": "Recent deploys, optionally per service.",
     "input_schema": {"type": "object",
        "properties": {"service": {"type": "string"}}}},
    {"name": "rollback", "description": "Roll back a deploy by id.",
     "input_schema": {"type": "object",
        "properties": {"deploy_id": {"type": "string"}}, "required": ["deploy_id"]}},
    {"name": "restart", "description": "Restart a service.",
     "input_schema": {"type": "object",
        "properties": {"service": {"type": "string"}}, "required": ["service"]}},
    {"name": "scale", "description": "Scale a service to N replicas.",
     "input_schema": {"type": "object",
        "properties": {"service": {"type": "string"},
                       "replicas": {"type": "integer"}}, "required": ["service"]}},
]

_READ = {"get_services", "get_metrics", "query_logs", "get_deploys"}
_ACT = {"rollback", "restart", "scale"}
ROLE_TOOLS = {
    "commander": _READ,
    "diagnostician": _READ,
    "remediator": _READ | _ACT,
    "comms": set(),
}

def tools_for(role: str) -> list[dict]:
    allowed = ROLE_TOOLS.get(role, set())
    return [t for t in TOOL_SCHEMAS if t["name"] in allowed]

def tools_for_openai(role: str) -> list[dict]:
    """Same per-role subset, but in OpenAI's function-tool shape
    ({"type":"function","function":{name,description,parameters}})."""
    return [
        {"type": "function", "function": {
            "name": t["name"], "description": t["description"],
            "parameters": t["input_schema"]}}
        for t in tools_for(role)
    ]

def tools_text(role: str) -> str:
    """Human-readable signature list for the prompt-based tool protocol (used instead of
    native function-calling, which is unreliable on some OpenAI-compatible providers)."""
    lines = []
    for t in tools_for(role):
        props = t["input_schema"].get("properties", {})
        req = set(t["input_schema"].get("required", []))
        params = ", ".join(
            f"{k}{'' if k in req else '?'}:{v.get('type','any')}" for k, v in props.items())
        lines.append(f'- {t["name"]}({params}) — {t["description"]}')
    return "\n".join(lines)

def dispatch(name: str, args: dict, ops) -> dict:
    if name == "get_services": return {"services": ops.get_services()}
    if name == "get_metrics":  return ops.get_metrics(args["service"])
    if name == "query_logs":   return {"lines": ops.query_logs(args["service"], args.get("level"))}
    if name == "get_deploys":  return {"deploys": ops.get_deploys(args.get("service"))}
    if name == "rollback":     return ops.rollback(args["deploy_id"])
    if name == "restart":      return ops.restart(args["service"])
    if name == "scale":        return ops.scale(args["service"], args.get("replicas", 4))
    return {"error": f"unknown tool {name}"}
