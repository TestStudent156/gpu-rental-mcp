"""Launch the whole War Room: server + bridge + detector + 4 LLM agents.

Each runs as its own subprocess; per-process stdout/stderr is redirected to app/logs/<name>.log
(unbuffered) so the coordination is observable. Ctrl-C stops everything.

Run from app/:  uv run python run_all.py

Prereqs: app/agent_config.yaml filled with all 6 agents' Band creds, app/.env with
ANTHROPIC_API_KEY, and all 6 agents added to one Band room.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

PROCS = []
LOGDIR = Path(__file__).resolve().parent / "logs"
LOGDIR.mkdir(exist_ok=True)


def spawn(args, label):
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    log = open(LOGDIR / f"{label}.log", "w", encoding="utf-8")
    print(f"[run_all] starting {label} -> logs/{label}.log", flush=True)
    PROCS.append((subprocess.Popen([sys.executable, *args], stdout=log, stderr=subprocess.STDOUT,
                                   env=env), log))


def main():
    spawn(["-m", "uvicorn", "warroom.server:app", "--port", "8000"], "server")
    time.sleep(2)
    spawn(["-m", "warroom.bridge"], "bridge")
    spawn(["-m", "warroom.detector_main"], "detector")
    time.sleep(1)
    for role in ["commander", "diagnostician", "remediator", "comms"]:
        spawn(["-m", "warroom.agent_main", "--role", role], role)
        time.sleep(1)

    print("\n[run_all] all up. Dashboard: http://127.0.0.1:8000/  Logs: app/logs/*.log")
    print("[run_all] Ctrl-C to stop.\n", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[run_all] stopping ...", flush=True)
        for p, log in PROCS:
            p.terminate()
            log.close()


if __name__ == "__main__":
    main()
