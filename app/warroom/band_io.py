"""Single point of contact with the Band SDK. Verified API + live findings:
see app/BAND_SDK_REFERENCE.md. The installed package imports as `band` (not thenvoi).

Coordination model (from the live spike):
  - send_message REQUIRES >=1 mention; mentions are handles like 'pokeyoke111/commander'.
  - inbound mentions appear in msg.content as '@[[<uuid>]]'.
  - an agent ACTS only when its own uuid is in the inbound content (it was addressed),
    and when it replies it @mentions its handoff target(s) by handle.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Awaitable, Callable, Optional
from band import Agent
from band.core import SimpleAdapter
from band.config import load_agent_config

WS_URL = "wss://app.band.ai/api/v1/socket/websocket"
REST_URL = "https://app.band.ai"


@dataclass
class Directory:
    """Maps role name -> Band handle, learned from participants_msg (provided on the
    bootstrap message). e.g. 'commander' -> 'pokeyoke111/commander'. Bare owner handles
    (the human users) are collected separately."""
    role_to_handle: dict = field(default_factory=dict)
    user_handles: list = field(default_factory=list)

    def update(self, participants_msg: Optional[str]):
        if not participants_msg:
            return
        for line in participants_msg.splitlines():
            m = re.search(r"@([^\s—-]+).*\((Agent|User)\)", line)
            if not m:
                continue
            handle, kind = m.group(1), m.group(2)
            if kind == "Agent":
                self.role_to_handle[handle.split("/")[-1].lower()] = handle
            elif handle not in self.user_handles:
                self.user_handles.append(handle)

    def all_agent_handles(self) -> list:
        return list(self.role_to_handle.values())

    def mentions_for(self, text: str, fallback: Optional[list] = None) -> list:
        """Resolve the @tokens in an agent's reply to Band handles."""
        low = text.lower()
        wanted: list = []
        if any(w in low for w in ("@all", "@everyone", "@team")):
            wanted = self.all_agent_handles()
        for tok in re.findall(r"@([a-z0-9_\-/]+)", low):
            role = tok.split("/")[-1]
            h = self.role_to_handle.get(role)
            if h and h not in wanted:
                wanted.append(h)
        if ("@user" in low or "@operator" in low):
            wanted += [h for h in self.user_handles if h not in wanted]
        if not wanted and fallback:
            wanted = [h for h in fallback if h]
        return wanted


@dataclass
class RoomHandle:
    """Captures a `tools` handle + room_id from on_message so other coroutines can send
    into the room proactively (detector alert, approval injection)."""
    _tools: object = None
    room_id: Optional[str] = None

    def bind(self, tools, room_id):
        self._tools = tools
        self.room_id = room_id

    async def send(self, content: str, mentions: Optional[list] = None):
        if self._tools is None:
            raise RuntimeError("RoomHandle not bound yet (no message seen)")
        await self._tools.send_message(content=content, mentions=mentions or [])


# handler(sender, content, tools, directory) -> awaitable
MessageHandler = Callable[[str, str, object, Directory], Awaitable[None]]


class BandAgentAdapter(SimpleAdapter):
    """Adapter for an LLM band member: binds RoomHandle + Directory on every message,
    and delegates to the handler ONLY when this agent was addressed (its uuid is in the
    inbound content), giving clean mention-driven turn-taking."""
    def __init__(self, self_agent_id: str, self_name: str,
                 room: RoomHandle, handler: MessageHandler, directory: Directory):
        super().__init__()  # REQUIRED: base sets history_converter/features/agent_name
        self._self_agent_id = self_agent_id
        self._self_name = self_name
        self._room = room
        self._handler = handler
        self._dir = directory
        # Stale-replay cutoff: ignore messages created more than this far before startup.
        # The grace absorbs clock skew between the Band server and this host so a genuinely
        # fresh trigger is never mistaken for stale (dropping a real trigger > keeping a stale).
        self._cutoff = datetime.now(timezone.utc) - timedelta(seconds=10)
        self._seen_ids: set = set()                    # ignore re-delivered backlog msgs

    async def on_message(self, msg, tools, history, participants_msg, contacts_msg, *,
                         is_session_bootstrap, room_id):
        self._room.bind(tools, room_id)
        self._dir.update(participants_msg)
        # NOTE: do NOT skip is_session_bootstrap — Band flags the FIRST message an agent
        # receives as bootstrap, and that first message is often the real one addressed to
        # us (e.g. the detector's alert). Skipping it drops the trigger. (Live spike finding.)
        if getattr(msg, "sender_id", None) == self._self_agent_id:
            return  # never react to our own messages
        # Drop messages left over from a PREVIOUS run: on (re)join Band replays room history,
        # whose created_at predates this process. Without this, old alerts re-trigger cascades.
        created = getattr(msg, "created_at", None)
        if isinstance(created, datetime):
            try:
                if created < self._cutoff:
                    return
            except TypeError:
                pass
        # Drop a message we've already handled: Band re-delivers backlog messages on resync
        # after a WebSocket blip, which would otherwise spawn duplicate LLM turns (and 429s).
        mid = getattr(msg, "id", None)
        if mid is not None:
            if mid in self._seen_ids:
                return
            self._seen_ids.add(mid)
        content = getattr(msg, "content", "") or ""
        addressed = (self._self_agent_id in content) or (f"@{self._self_name}" in content.lower())
        if not addressed:
            return  # observe only — not our turn
        sender = getattr(msg, "sender_name", None) or getattr(msg, "sender_id", "")
        await self._handler(sender, content, tools, self._dir)

    async def on_cleanup(self, room_id):
        pass


async def make_agent(config_name: str, adapter_factory) -> Agent:
    """Load creds from agent_config.yaml, build the adapter via adapter_factory(agent_id),
    and create the Band agent.

    NOTE: Agent.create is SYNCHRONOUS (live spike 2026-06-12) — do not await it. make_agent
    stays async so callers keep `await make_agent(...)`."""
    agent_id, api_key = load_agent_config(config_name)
    adapter = adapter_factory(agent_id)
    return Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key,
                        ws_url=WS_URL, rest_url=REST_URL)
