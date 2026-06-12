"""Silent Band participant that bridges the room to the ops dashboard.

Responsibilities (it never reasons — pure plumbing):
  1. Mirror every room message to the server's /timeline -> SSE -> dashboard.
  2. Detect the commander's "APPROVAL REQUESTED: <action> on <service>" and open a
     pending approval on the server (which surfaces the APPROVE/REJECT button).
  3. Poll the server for the human's decision and inject it back into the Band room
     (so the remediator, watching the room, sees "APPROVED" and proceeds).

Verified Band API: see app/BAND_SDK_REFERENCE.md. Run from app/: `python -m warroom.bridge`.

LIVE-SPIKE UNKNOWNS to confirm with real creds:
  - Proactive send: _approval_poll() reuses a cached `tools` handle (RoomHandle) to send
    outside on_message. Confirm a cached handle works.
"""
import asyncio
import httpx
from dotenv import load_dotenv
from band.core import SimpleAdapter
from warroom.band_io import RoomHandle, Directory, make_agent

BASE = "http://127.0.0.1:8000"


class BridgeAdapter(SimpleAdapter):
    def __init__(self, self_agent_id, room: RoomHandle, directory: Directory):
        super().__init__()  # REQUIRED: base sets history_converter/features/etc.
        self._self_agent_id = self_agent_id
        self._room = room
        self._dir = directory
        self._http = httpx.AsyncClient(base_url=BASE, timeout=10)
        self._last_request = ""  # the action+service text the commander asked approval for

    async def on_started(self, agent_name, agent_description):
        # Start polling for human approval decisions in the background.
        asyncio.create_task(self._approval_poll())

    async def on_message(self, msg, tools, history, participants_msg, contacts_msg, *,
                         is_session_bootstrap, room_id):
        self._room.bind(tools, room_id)
        self._dir.update(participants_msg)
        # Mirror every message including the first (bootstrap) one — that's often the
        # opening alert we want on the timeline. Just skip our own messages.
        if getattr(msg, "sender_id", None) == self._self_agent_id:
            return
        sender = getattr(msg, "sender_name", None) or getattr(msg, "sender_id", "")
        content = getattr(msg, "content", "") or ""

        # 1. Mirror to the dashboard timeline.
        try:
            await self._http.post("/timeline", json={"sender": sender, "content": content})
        except Exception:
            pass

        # 2. Detect an approval request from the commander.
        if "APPROVAL REQUESTED" in content:
            try:
                body = content.split("APPROVAL REQUESTED:", 1)[1].strip()
                action, _, service = body.partition(" on ")
                self._last_request = body.rstrip(".").strip()  # remember exactly what was asked
                await self._http.post("/approval/request", json={
                    "action": action.strip().rstrip(".").strip(),
                    "service": service.strip().rstrip(".").strip(),
                })
            except Exception:
                pass

    async def _approval_poll(self):
        """When the human clicks APPROVE/REJECT, the server records a one-shot decision
        at /approval/last. Relay it into the room as a governance message."""
        while True:
            await asyncio.sleep(1.0)
            if not self._room.room_id:
                continue
            try:
                decision = (await self._http.get("/approval/last")).json().get("decision")
                if decision:
                    # Address the remediator (who is waiting on approval) + the commander.
                    targets = [self._dir.role_to_handle.get(r) for r in ("remediator", "commander")]
                    targets = [t for t in targets if t]
                    if targets:
                        # Agent turns are stateless, so the remediator has no memory of what it
                        # proposed. Echo the exact approved action back so it executes precisely
                        # that (don't make a small model re-derive the fix from scratch).
                        if decision == "APPROVED" and self._last_request:
                            text = (f"@remediator APPROVED by human operator. Execute exactly this "
                                    f"now via your action tool: {self._last_request}")
                        else:
                            text = f"@remediator {decision} by human operator"
                        await self._room.send(text, mentions=targets)
            except Exception:
                pass

    async def on_cleanup(self, room_id):
        pass


async def main():
    load_dotenv()
    room = RoomHandle()
    directory = Directory()
    agent = await make_agent("bridge", lambda aid: BridgeAdapter(aid, room, directory))
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
