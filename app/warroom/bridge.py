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
from warroom.band_io import RoomHandle, make_agent

BASE = "http://127.0.0.1:8000"


class BridgeAdapter(SimpleAdapter):
    def __init__(self, self_agent_id, room: RoomHandle):
        self._self_agent_id = self_agent_id
        self._room = room
        self._http = httpx.AsyncClient(base_url=BASE, timeout=10)

    async def on_started(self, agent_name, agent_description):
        # Start polling for human approval decisions in the background.
        asyncio.create_task(self._approval_poll())

    async def on_message(self, msg, tools, history, participants_msg, contacts_msg, *,
                         is_session_bootstrap, room_id):
        self._room.bind(tools, room_id)
        if is_session_bootstrap:
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
                    await self._room.send(f"{decision} by human operator", mentions=[])
            except Exception:
                pass

    async def on_cleanup(self, room_id):
        pass


async def main():
    load_dotenv()
    room = RoomHandle()
    agent = await make_agent("bridge", lambda aid: BridgeAdapter(aid, room))
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
