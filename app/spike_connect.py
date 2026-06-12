"""Throwaway Band connectivity spike. Confirms the 4 unknowns in BAND_SDK_REFERENCE.md:
  1. agent connects + on_message fires
  2. message field shapes (sender_id / sender_name / content)
  3. tools.send_message posts a reply
  4. a CACHED tools handle works for a proactive send outside on_message

Run from app/:  uv run python spike_connect.py
Then send a message to the 'commander' agent in your Band room. Watch the prints.
"""
import asyncio
from dotenv import load_dotenv
from band.core import SimpleAdapter
from warroom.band_io import make_agent


class SpikeAdapter(SimpleAdapter):
    def __init__(self, self_agent_id, cache):
        super().__init__()  # REQUIRED: sets history_converter/features/etc. on the base
        self._id = self_agent_id
        self._cache = cache

    async def on_started(self, agent_name, agent_description):
        print(f"[STARTED] name={agent_name!r} my_id={self._id}", flush=True)

    async def on_message(self, msg, tools, history, participants_msg, contacts_msg, *,
                         is_session_bootstrap, room_id):
        print(f"[MSG] bootstrap={is_session_bootstrap} room={room_id}", flush=True)
        print(f"      sender_id={getattr(msg,'sender_id',None)!r} "
              f"sender_name={getattr(msg,'sender_name',None)!r} "
              f"sender_type={getattr(msg,'sender_type',None)!r}", flush=True)
        print(f"      content={getattr(msg,'content',None)!r}", flush=True)
        print(f"      history_type={type(history).__name__} "
              f"participants_msg={participants_msg!r}", flush=True)
        self._cache["tools"] = tools
        self._cache["room_id"] = room_id
        if is_session_bootstrap:
            return
        if getattr(msg, "sender_id", None) == self._id:
            print("      (own message — skipping reply)", flush=True)
            return
        try:
            await tools.send_message(content="ack from spike", mentions=[])
            print("      [SEND OK] replied 'ack from spike'", flush=True)
        except Exception as e:
            print(f"      [SEND FAILED] {e!r}", flush=True)

        async def delayed():
            await asyncio.sleep(5)
            try:
                await tools.send_message(content="proactive ping (cached handle)", mentions=[])
                print("[PROACTIVE OK] cached tools handle works outside on_message", flush=True)
            except Exception as e:
                print(f"[PROACTIVE FAILED] {e!r}", flush=True)
        asyncio.create_task(delayed())

    async def on_cleanup(self, room_id):
        print(f"[CLEANUP] {room_id}", flush=True)


async def main():
    load_dotenv()
    cache = {}
    agent = await make_agent("commander", lambda aid: SpikeAdapter(aid, cache))
    print("[CONNECTING] commander — now send it a message in the Band room ...", flush=True)
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
