# Band SDK — verified API reference

Source: live introspection of installed `band-sdk==1.0.0` (imports as `band`) on 2026-06-12.
This OVERRIDES the snippets in `docs/superpowers/plans/2026-06-12-war-room.md`, which were
written against stale docs that used the `thenvoi` namespace. When implementing any Band-
touching task (plan Tasks 1, 7-main, 9, 10), use the names here.

## Install / import
- Package: `band-sdk[anthropic]`. Imports as **`band`** (NOT `thenvoi`).
- Run commands from the `app/` dir: `uv run --directory app python ...` (or cd into `app`).

## Agent
```python
from band import Agent
from band.config import load_agent_config   # (agent_key, *, config_path=None) -> (agent_id, api_key); reads agent_config.yaml

agent_id, api_key = load_agent_config("commander")
agent = await Agent.create(           # NOTE: create is ASYNC — must await
    adapter=adapter,
    agent_id=agent_id,
    api_key=api_key,
    ws_url="wss://app.band.ai/api/v1/socket/websocket",  # default; can omit
    rest_url="https://app.band.ai",                      # default; can omit
)
await agent.start()
await agent.run(shutdown_timeout=30.0)   # blocks until interrupt
await agent.stop()
# Alternative one-liner that reads agent_config.yaml for you:
# agent = await Agent.from_config("commander", adapter=adapter)
```
`agent.is_running`, `agent.agent_name`, `agent.agent_description`, `agent.runtime`.

## Custom adapter (our approach: call Anthropic ourselves)
```python
from band.core import SimpleAdapter   # NOT band.adapters

class MyAdapter(SimpleAdapter):
    async def on_started(self, agent_name: str, agent_description: str) -> None: ...
    async def on_message(
        self, msg, tools, history, participants_msg, contacts_msg, *,
        is_session_bootstrap: bool, room_id: str,
    ) -> None: ...
    async def on_cleanup(self, room_id: str) -> None: ...
```
- `on_message` has SIX positional params: `msg, tools, history, participants_msg, contacts_msg`
  then keyword-only `is_session_bootstrap`, `room_id`. (Plan omitted `contacts_msg` — include it.)

## Inbound message — `PlatformMessage` (band.runtime.types)
Fields: `id, room_id, content, sender_id, sender_type, sender_name, message_type, metadata, created_at`.
- Read text: `msg.content`
- Read sender: `msg.sender_name or msg.sender_id` (there is NO `msg.sender` object).
- Loop-prevention: skip when `msg.sender_id == <our own agent_id>` (track it on the adapter).

## Room operations — on the `tools` arg (band.runtime.tools.AgentTools), all async
```python
await tools.send_message(content: str, mentions: list[str] | None = None)
await tools.send_event(content: str, message_type: str, metadata: dict | None = None)
chatroom_id = await tools.create_chatroom(task_id: str | None = None)
await tools.add_participant(identifier: str, role: str = "member")
await tools.remove_participant(identifier: str)
peers = await tools.lookup_peers(page: int = 1, page_size: int = 50)
parts = await tools.get_participants()
ctx = await tools.fetch_room_context(room_id=..., page=1, page_size=50)
# also: get_anthropic_tool_schemas(), get_openai_tool_schemas(), memory + contact methods
```
- Method is `send_message`, NOT `thenvoi_send_message`. (The `band_`-prefixed names like
  `band_send_message` are the MCP/LLM-tool layer used by framework adapters, not the Python call.)

## Env vars
- The SDK reads `BAND_*` only in some CLI entrypoints (`BAND_API_KEY`, `BAND_AGENT_ID`,
  `BAND_REST_URL`). The core `Agent.create` path takes explicit args; creds come from
  `agent_config.yaml`. There is NO `THENVOI_*` and no env-based WS URL.
- Our `.env` realistically needs only: `ANTHROPIC_API_KEY`. (Optionally `BAND_REST_URL`.)

## Proactive send (plan spike unknown #4 — still verify live)
No confirmed agent-level "send into room X" call was found in introspection. Plan: cache the
`tools` handle (and `room_id`) from the first `on_message` and reuse it for proactive sends
(detector alert, approval injection). `tools.create_chatroom` exists if we need to make a room.
Confirm during the live spike whether a cached `tools` works outside the on_message call.

## Adapters available (band.adapters, lazy-loaded)
`AnthropicAdapter`, `ClaudeSDKAdapter`, `LangGraphAdapter`, `PydanticAIAdapter`, `CrewAIAdapter`,
`ParlantAdapter`, `CodexAdapter`, `GeminiAdapter`, `GoogleADKAdapter`, `LettaAdapter`,
`SlackAdapter`, `A2AAdapter`, `ACPClientAdapter`, etc. (We use a custom `SimpleAdapter` subclass
for full control over role prompts + MockOps tools.)
```
