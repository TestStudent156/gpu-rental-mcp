"""The Detector as a minimal, non-LLM Band participant.

It polls the server's /status, runs the deterministic threshold Detector, and when a NEW
incident appears it raises an alert into the Band room addressed to @commander. This is the
event that kicks off the whole war-room coordination.

Verified Band API: see app/BAND_SDK_REFERENCE.md. Run from app/: `python -m warroom.detector_main`.

LIVE-SPIKE UNKNOWNS to confirm with real creds:
  - Proactive send: _loop() reuses a cached `tools` handle (RoomHandle) bound on the first
    inbound message. If the SDK never delivers an inbound message to bind against, seed the
    room once from the Band UI (or have the commander greet on join) so the handle binds.
  - Mention format: send_message(mentions=["commander"]) — confirm whether mentions take the
    agent's display name, handle, or UUID.
"""
import asyncio
import httpx
from dotenv import load_dotenv
from band.core import SimpleAdapter
from warroom.band_io import RoomHandle, Directory, make_agent
from warroom.detector import Detector

BASE = "http://127.0.0.1:8000"


class DetectorAdapter(SimpleAdapter):
    def __init__(self, self_agent_id, room: RoomHandle, directory: Directory):
        super().__init__()  # REQUIRED: base sets history_converter/features/etc.
        self._room = room
        self._dir = directory
        self._det = Detector()
        self._http = httpx.AsyncClient(base_url=BASE, timeout=10)

    async def on_started(self, agent_name, agent_description):
        asyncio.create_task(self._loop())

    async def on_message(self, msg, tools, history, participants_msg, contacts_msg, *,
                         is_session_bootstrap, room_id):
        # Capture a room handle (for proactive sends) and the handle directory.
        self._room.bind(tools, room_id)
        self._dir.update(participants_msg)

    async def _loop(self):
        while True:
            await asyncio.sleep(2.0)
            if not self._room.room_id:
                continue
            commander = self._dir.role_to_handle.get("commander")
            if not commander:
                continue  # wait until we know the commander's handle
            try:
                services = (await self._http.get("/status")).json()["services"]
            except Exception:
                continue
            for a in self._det.poll(services):
                await self._room.send(
                    f"@commander 🚨 ALERT [{a['severity']}] {a['service']}: {a['reason']}",
                    mentions=[commander],
                )

    async def on_cleanup(self, room_id):
        pass


async def main():
    load_dotenv()
    room = RoomHandle()
    directory = Directory()
    agent = await make_agent("detector", lambda aid: DetectorAdapter(aid, room, directory))
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
