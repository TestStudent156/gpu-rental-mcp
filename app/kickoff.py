"""Post a message into the EXISTING Band room (BAND_ROOM_ID) via the REST API, as the
detector, mentioning the commander. This bootstraps all agents and kicks off the flow
WITHOUT needing a human to post a seed message.

Run from app/:  uv run python kickoff.py  [optional message]
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
from band.config import load_agent_config
from band.cli.trigger import find_peer_by_handle
from thenvoi_rest import AsyncRestClient, ChatMessageRequest, ChatMessageRequestMentionsItem

REST = "https://app.band.ai"
TARGET = "@pokeyoke111/commander"
DEFAULT_MSG = ("@commander 🚨 ALERT [critical] checkout: error_rate=42% — incident reported, "
               "please coordinate triage and remediation.")


async def main():
    load_dotenv()
    room_id = os.environ.get("BAND_ROOM_ID")
    if not room_id:
        print("ERROR: BAND_ROOM_ID not set in app/.env"); return
    message = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MSG
    _, api_key = load_agent_config("detector")
    client = AsyncRestClient(api_key=api_key, base_url=REST)
    try:
        peer = await find_peer_by_handle(client, TARGET, "agent")
        print("commander peer lookup:", peer)
        if not peer:
            print("ERROR: could not find commander peer; check owner handle in TARGET"); return
        mention = ChatMessageRequestMentionsItem(id=peer["id"], handle=peer["handle"])
        req = ChatMessageRequest(content=message, mentions=[mention])
        await client.agent_api_messages.create_agent_chat_message(chat_id=room_id, message=req)
        print(("posted to room " + room_id + ": " + message).encode("ascii", "replace").decode())
    finally:
        await client._client_wrapper.httpx_client.httpx_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
