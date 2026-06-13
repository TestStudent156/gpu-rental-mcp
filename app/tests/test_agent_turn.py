import asyncio, types
import warroom.agent_main as am
from warroom.roles import ROLES
from warroom.mockops import MockOps
from warroom.tools import dispatch

class LocalOps:
    def __init__(self, ops): self.ops = ops
    def call(self, name, args): return dispatch(name, args, self.ops)

class FakeOpenAI:
    """chat.completions.create: emit a JSON tool-call once, then a final plain-text reply."""
    def __init__(self): self.calls = 0
    class _CC:
        def __init__(self, outer): self.outer = outer
        def create(self, **kw):
            self.outer.calls += 1
            if self.outer.calls == 1:
                content = '{"tool": "get_metrics", "args": {"service": "checkout"}}'
            else:
                content = "Root cause: bad deploy dpl-104"
            msg = types.SimpleNamespace(content=content)
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])
    @property
    def chat(self):
        return types.SimpleNamespace(completions=FakeOpenAI._CC(self))

def test_turn_runs_tool_then_returns_text(monkeypatch):
    # Bypass the server-side LLM concurrency gate in this unit test.
    async def direct(client, **kw):
        return client.chat.completions.create(**kw)
    monkeypatch.setattr(am, "_gated_create", direct)

    ops = MockOps(); ops.inject("bad_deploy")
    out = asyncio.run(am.run_claude_turn(FakeOpenAI(), ROLES["diagnostician"],
                                         "alert: checkout error_rate high", LocalOps(ops)))
    assert "dpl-104" in out

def test_parse_action_handles_truncated_and_prose():
    assert am._parse_action('{"tool":"get_metrics","args":{"service":"checkout"}}\n{"tool":"x"') \
        == ("get_metrics", {"service": "checkout"})
    assert am._parse_action("@commander root cause is dpl-104") is None
