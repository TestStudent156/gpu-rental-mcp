"""One-command demo trigger.

Injects the incident into the ops simulator (degrades checkout) and then raises the alert
into the Band room (mentioning the commander), which kicks off the whole war-room cascade.

Run:  uv run --directory app python demo_trigger.py            # default: bad_deploy
      uv run --directory app python demo_trigger.py memory_leak
"""
import asyncio
import sys
import httpx
from kickoff import main as kickoff_main

SERVER = "http://127.0.0.1:8000"


def main():
    scenario = sys.argv[1] if len(sys.argv) > 1 else "bad_deploy"
    r = httpx.post(f"{SERVER}/inject", json={"scenario": scenario}, timeout=10)
    print(f"injected {scenario}: {r.json()}")
    asyncio.run(kickoff_main())


if __name__ == "__main__":
    main()
