"""Run one band member: python -m warroom.agent_main --role diagnostician"""
import argparse, asyncio
import anthropic
from dotenv import load_dotenv
from warroom.roles import ROLES
from warroom.tools import tools_for
from warroom.band_io import BandAgentAdapter, RoomHandle, make_agent

MAX_TOOL_HOPS = 6


async def run_claude_turn(client, role, user_text, ops_client) -> str:
    """One agent 'turn': feed incoming room text to Claude, run the tool loop against
    ops_client (which adapts our tool calls onto MockOps), return final text for the room."""
    tools = tools_for(role.name)
    messages = [{"role": "user", "content": user_text}]
    text = ""
    for _ in range(MAX_TOOL_HOPS):
        kwargs = dict(model=role.model, max_tokens=1024,
                      system=role.system_prompt, messages=messages)
        if tools:
            kwargs["tools"] = tools
        resp = client.messages.create(**kwargs)
        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        text = "".join(b.text for b in resp.content if b.type == "text")
        if not tool_uses:
            return text
        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for tu in tool_uses:
            out = ops_client.call(tu.name, tu.input)
            results.append({"type": "tool_result", "tool_use_id": tu.id,
                            "content": str(out)})
        messages.append({"role": "user", "content": results})
    return text or "(no response)"


class HttpOps:
    """ops_client that calls the server's HTTP action API (Task 8)."""
    def __init__(self, base="http://127.0.0.1:8000"):
        import httpx
        self._c = httpx.Client(base_url=base, timeout=30)
    def call(self, name, args):
        return self._c.post(f"/ops/{name}", json=args).json()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", required=True, choices=list(ROLES))
    args = ap.parse_args()
    load_dotenv()
    role = ROLES[args.role]
    client = anthropic.Anthropic()
    ops_client = HttpOps()
    room = RoomHandle()

    async def handle(sender, content, tools):
        reply = await run_claude_turn(client, role, f"[{sender}] {content}", ops_client)
        if reply and reply.strip():
            await tools.send_message(content=reply, mentions=[])

    def adapter_factory(self_agent_id):
        return BandAgentAdapter(self_agent_id, role.name, room, handle)

    agent = await make_agent(role.name, adapter_factory)
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
