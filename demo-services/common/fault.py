"""Exec-only, automatically expiring fault state for one demo container."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

FAULT_FILE = Path("/tmp/sentinel-demo-fault.json")
SCENARIOS = ("latency", "errors", "runtime-pressure", "queue-backlog")


def active_fault() -> dict[str, float | str] | None:
    try:
        fault = json.loads(FAULT_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    if float(fault.get("expires_at", 0)) <= time.time():
        FAULT_FILE.unlink(missing_ok=True)
        return None
    return fault


def main() -> None:
    parser = argparse.ArgumentParser(description="Enable a local demo fault inside this container.")
    parser.add_argument("scenario", choices=SCENARIOS, nargs="?")
    parser.add_argument("--duration", type=int, default=60, choices=range(15, 601))
    parser.add_argument("--clear", action="store_true")
    args = parser.parse_args()
    if args.clear:
        FAULT_FILE.unlink(missing_ok=True)
        return
    if args.scenario is None:
        parser.error("scenario is required unless --clear is used")
    FAULT_FILE.write_text(json.dumps({"scenario": args.scenario, "expires_at": time.time() + args.duration}))


if __name__ == "__main__":
    main()
