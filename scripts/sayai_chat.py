#!/usr/bin/env python3
"""
SayAi REPL chat against the HTTP API (no SDK dependency beyond httpx).

  pip install httpx
  export SAYAI_API_URL=http://127.0.0.1:8000
  python scripts/sayai_chat.py --email you@example.com --password 'secret'

Or reuse a token:

  export SAYAI_TOKEN='eyJ...'
  python scripts/sayai_chat.py

Commands: /mode chat|agent   /new   /quit
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any


def _die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def main() -> None:
    try:
        import httpx
    except ImportError:
        _die("Install httpx: pip install httpx")

    p = argparse.ArgumentParser(description="SayAi CLI chat")
    p.add_argument("--url", default=os.environ.get("SAYAI_API_URL", "http://127.0.0.1:8000"))
    p.add_argument("--email", default=os.environ.get("SAYAI_EMAIL"))
    p.add_argument("--password", default=os.environ.get("SAYAI_PASSWORD"))
    p.add_argument("--token", default=os.environ.get("SAYAI_TOKEN"))
    p.add_argument("--mode", choices=("chat", "agent"), default="chat")
    args = p.parse_args()
    base = args.url.rstrip("/")
    token: str | None = args.token
    mode: str = args.mode
    session_id: str | None = None

    with httpx.Client(base_url=base, timeout=320.0) as client:
        if not token:
            if not args.email or not args.password:
                _die("Provide --email and --password, or set SAYAI_TOKEN")
            r = client.post(
                "/api/v1/auth/login",
                json={"email": args.email, "password": args.password},
            )
            if r.status_code != 200:
                _die(f"Login failed: {r.status_code} {r.text}")
            token = r.json().get("access_token")
            if not token:
                _die("No access_token in login response")

        headers = {"Authorization": f"Bearer {token}"}

        print(f"SayAi CLI — {base} — mode={mode}. /mode chat|agent  /new  /quit\n")

        while True:
            try:
                line = input("You> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not line:
                continue
            if line in ("/quit", "/exit", ":q"):
                break
            if line.startswith("/mode "):
                m = line.split(maxsplit=1)[1].strip().lower()
                if m in ("chat", "agent"):
                    mode = m
                    print(f"(mode → {mode})")
                else:
                    print("Usage: /mode chat|agent")
                continue
            if line == "/new":
                session_id = None
                print("(new session)")
                continue

            body: dict[str, Any] = {
                "mode": mode,
                "message": line,
                "await_completion": True,
                "tools_enabled": mode == "agent",
            }
            if session_id:
                body["session_id"] = session_id

            r = client.post("/api/v1/runs", json=body, headers=headers)
            if r.status_code != 200:
                print(f"Error: {r.status_code} {r.text}")
                continue
            created = r.json()
            session_id = created.get("session_id") or session_id
            run_id = created.get("run_id")
            if not run_id:
                print("Error: no run_id", created)
                continue

            r2 = client.get(f"/api/v1/runs/{run_id}", headers=headers)
            if r2.status_code != 200:
                print(f"Error fetching run: {r2.status_code} {r2.text}")
                continue
            run = r2.json()
            if run.get("status") == "failed":
                print(f"Assistant> (failed) {run.get('error')}")
            else:
                summary = run.get("summary") or {}
                text = summary.get("assistant") or "(no reply)"
                print(f"Assistant> {text}")


if __name__ == "__main__":
    main()
