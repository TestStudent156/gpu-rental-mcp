"""Run one band member: python -m warroom.agent_main --role diagnostician"""
import argparse, asyncio, json
import httpx
import openai
from openai import OpenAI
from dotenv import load_dotenv
from warroom.roles import ROLES
from warroom.tools import tools_text
from warroom.band_io import BandAgentAdapter, RoomHandle, Directory, make_agent

MAX_TOOL_HOPS = 6
SERVER = "http://127.0.0.1:8000"

_PROTOCOL = (
    "\n\nYOU HAVE TOOLS. To call one, reply with ONLY a single JSON object and nothing "
    'else:\n{{"tool": "<name>", "args": {{...}}}}\n'
    "Call EXACTLY ONE tool per reply, using the exact tool name from the list below. You "
    "will then receive the tool result and may call another tool. When you are done "
    "investigating/acting and ready to speak to the room, reply with a normal plain-text "
    "message (NOT JSON). Available tools:\n{tools}")


async def _create_with_retry(client, **kwargs):
    """Backstop 429 retry. The server LLM gate should already serialize calls to the single
    available concurrency unit, but if a lease lapses and two slip through, back off."""
    delay = 2.0
    for attempt in range(6):
        try:
            return client.chat.completions.create(**kwargs)
        except openai.RateLimitError:
            if attempt == 5:
                raise
            await asyncio.sleep(delay)
            delay = min(delay * 1.6, 20.0)


async def _gated_create(client, **kwargs):
    """Acquire the server's single LLM slot, make the call, then release. Agents are separate
    processes; this gate is how they share the one concurrency unit without colliding."""
    async with httpx.AsyncClient(base_url=SERVER, timeout=15) as gate:
        for _ in range(300):  # wait up to ~150s for the slot
            try:
                if (await gate.post("/llm/acquire")).json().get("granted"):
                    break
            except Exception:
                pass
            await asyncio.sleep(0.5)
        try:
            return await _create_with_retry(client, **kwargs)
        finally:
            try:
                await gate.post("/llm/release")
            except Exception:
                pass


def _iter_json_objects(text: str):
    """Yield each top-level {...} substring (brace-matched), tolerating prose, code fences,
    and trailing truncated objects around them."""
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0:
                yield text[start:i + 1]


def _parse_action(text: str):
    """Return (tool_name, args) for the FIRST well-formed tool-call object in the reply, or
    None if the reply is a plain room message. Robust to multiple / truncated JSON blocks."""
    if not text:
        return None
    for c in _iter_json_objects(text):
        try:
            obj = json.loads(c)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("tool"), str):
            return obj["tool"], (obj.get("args") or {})
    return None


async def run_claude_turn(client, role, user_text, ops_client) -> str:
    """One agent 'turn': feed incoming room text to the LLM, run a prompt-based tool loop
    against ops_client (which adapts our tool calls onto MockOps), return final text for the
    room. Uses a JSON action protocol rather than native function-calling, which is flaky on
    some OpenAI-compatible providers (Band itself is LLM-agnostic; the brain is ours)."""
    tools = tools_text(role.name)
    system = role.system_prompt + (_PROTOCOL.format(tools=tools) if tools else "")
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user_text}]
    text = ""
    for _ in range(MAX_TOOL_HOPS):
        resp = await _gated_create(
            client, model=role.model, max_tokens=1024, messages=messages)
        text = resp.choices[0].message.content or ""
        action = _parse_action(text)
        if not action:
            return text
        name, tc_args = action
        out = ops_client.call(name, tc_args)
        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user",
                         "content": f"Result of {name}: {out}"})
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
    client = OpenAI()
    ops_client = HttpOps()
    room = RoomHandle()
    directory = Directory()

    async def handle(sender, content, tools, directory):
        print(f"[{role.name}] <- {sender}: {content[:100]}", flush=True)
        reply = await run_claude_turn(client, role, f"[{sender}] {content}", ops_client)
        if not (reply and reply.strip()):
            print(f"[{role.name}] (no reply)", flush=True)
            return
        # Band requires >=1 mention. Resolve @tokens in the reply to handles; if the LLM
        # addressed no one, fall back to the commander (or, for the commander, to all agents).
        if role.name == "commander":
            fallback = directory.all_agent_handles()
        else:
            fallback = [directory.role_to_handle.get("commander")]
        mentions = directory.mentions_for(reply, fallback=fallback)
        # Band rejects a message that @mentions its own sender ('cannot_mention_self').
        self_handle = directory.role_to_handle.get(role.name)
        mentions = [m for m in mentions if m and m != self_handle]
        print(f"[{role.name}] -> {mentions}: {reply[:120]}", flush=True)
        if mentions:
            await tools.send_message(content=reply, mentions=mentions)
        else:
            print(f"[{role.name}] !! no mentions resolved, message NOT sent", flush=True)

    def adapter_factory(self_agent_id):
        return BandAgentAdapter(self_agent_id, role.name, room, handle, directory)

    agent = await make_agent(role.name, adapter_factory)
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
