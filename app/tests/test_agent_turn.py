import asyncio, types
from warroom.roles import ROLES
from warroom.mockops import MockOps
from warroom.tools import dispatch

class LocalOps:
    def __init__(self, ops): self.ops = ops
    def call(self, name, args): return dispatch(name, args, self.ops)

class FakeClaude:
    """Returns a tool_use once, then a final text."""
    def __init__(self): self.calls = 0
    class _Msgs:
        def __init__(self, outer): self.outer = outer
        def create(self, **kw):
            self.outer.calls += 1
            if self.outer.calls == 1:
                tu = types.SimpleNamespace(type="tool_use", id="t1",
                        name="get_metrics", input={"service": "checkout"})
                return types.SimpleNamespace(content=[tu])
            txt = types.SimpleNamespace(type="text", text="Root cause: bad deploy dpl-104")
            return types.SimpleNamespace(content=[txt])
    @property
    def messages(self): return FakeClaude._Msgs(self)

def test_turn_runs_tool_then_returns_text():
    from warroom.agent_main import run_claude_turn
    ops = MockOps(); ops.inject("bad_deploy")
    out = asyncio.run(run_claude_turn(FakeClaude(), ROLES["diagnostician"],
                                      "alert: checkout error_rate high", LocalOps(ops)))
    assert "dpl-104" in out
