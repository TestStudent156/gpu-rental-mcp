"""Single point of contact with the Band SDK. Verified API: see app/BAND_SDK_REFERENCE.md.
The installed package imports as `band` (not thenvoi)."""
import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional
from band import Agent
from band.core import SimpleAdapter
from band.config import load_agent_config

WS_URL = "wss://app.band.ai/api/v1/socket/websocket"
REST_URL = "https://app.band.ai"


@dataclass
class RoomHandle:
    """Captures a `tools` handle + room_id from on_message so other coroutines can
    send into the room proactively (detector alert, approval injection). The live spike
    confirms whether a cached `tools` works outside on_message."""
    _tools: object = None
    room_id: Optional[str] = None

    def bind(self, tools, room_id):
        self._tools = tools
        self.room_id = room_id

    async def send(self, content: str, mentions: Optional[list] = None):
        if self._tools is None:
            raise RuntimeError("RoomHandle not bound yet (no message seen)")
        await self._tools.send_message(content=content, mentions=mentions or [])


# handler(sender: str, content: str, tools) -> awaitable
MessageHandler = Callable[[str, str, object], Awaitable[None]]


class BandAgentAdapter(SimpleAdapter):
    """Generic adapter: binds the RoomHandle on every message and delegates inbound
    messages (not our own, not bootstrap) to an async handler."""
    def __init__(self, self_agent_id: str, self_name: str,
                 room: RoomHandle, handler: MessageHandler):
        self._self_agent_id = self_agent_id
        self._self_name = self_name
        self._room = room
        self._handler = handler

    async def on_started(self, agent_name, agent_description):
        pass

    async def on_message(self, msg, tools, history, participants_msg, contacts_msg, *,
                         is_session_bootstrap, room_id):
        self._room.bind(tools, room_id)
        if is_session_bootstrap:
            return
        if getattr(msg, "sender_id", None) == self._self_agent_id:
            return  # ignore our own messages (loop prevention)
        sender = getattr(msg, "sender_name", None) or getattr(msg, "sender_id", "")
        content = getattr(msg, "content", "")
        await self._handler(sender, content, tools)

    async def on_cleanup(self, room_id):
        pass


async def make_agent(config_name: str, adapter_factory) -> Agent:
    """Load creds from agent_config.yaml, build the adapter (which needs our own
    agent_id for loop-prevention), and create the Band agent. Agent.create is async."""
    agent_id, api_key = load_agent_config(config_name)
    adapter = adapter_factory(agent_id)
    return await Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key,
                              ws_url=WS_URL, rest_url=REST_URL)
