"""Launch the whole War Room: server + bridge + detector + 4 LLM agents.

Each runs as its own subprocess (mirrors production: agents are independent processes that
only meet in the Band room). Ctrl-C stops everything.

Run from app/:  uv run python run_all.py

Prereqs: app/agent_config.yaml filled with all 6 agents' Band creds, app/.env with
ANTHROPIC_API_KEY, and all 6 agents added to one Band room.
"""
import subprocess
import sys
import time

PROCS = []


def spawn(args, label):
    print(f"[run_all] starting {label} ...")
    PROCS.append(subprocess.Popen([sys.executable, *args]))


def main():
    # 1. Server first (sim env + dashboard + SSE + approval API).
    spawn(["-m", "uvicorn", "warroom.server:app", "--port", "8000"], "server")
    time.sleep(2)

    # 2. Non-LLM Band infrastructure agents.
    spawn(["-m", "warroom.bridge"], "bridge")
    spawn(["-m", "warroom.detector_main"], "detector")
    time.sleep(1)

    # 3. The LLM band members.
    for role in ["commander", "diagnostician", "remediator", "comms"]:
        spawn(["-m", "warroom.agent_main", "--role", role], role)
        time.sleep(1)

    print("\n[run_all] all processes up. Open the dashboard at http://127.0.0.1:8000/")
    print("[run_all] trigger an incident with:")
    print('  curl -X POST http://127.0.0.1:8000/inject '
          '-H "Content-Type: application/json" -d "{\\"scenario\\":\\"bad_deploy\\"}"')
    print("[run_all] Ctrl-C to stop everything.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[run_all] stopping all processes ...")
        for p in PROCS:
            p.terminate()


if __name__ == "__main__":
    main()
