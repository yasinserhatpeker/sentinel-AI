"""Bounded Redis-backed fault state for local demo services."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import time

import redis

SCENARIOS = ("latency", "errors", "database-slowdown", "queue-backlog")
MAX_DURATION_SECONDS = 600
MAX_DELAY_MS = 5000
FAULT_SCHEMA_VERSION = "fault-state.v1"
FAULT_KEY_PREFIX = "sentinelai:fault:v1"


class FaultStateUnavailable(RuntimeError):
    """Raised for control mutations when Redis cannot confirm the state."""


def _service_name() -> str:
    service = os.environ.get("SENTINEL_SERVICE_NAME", "")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", service):
        raise FaultStateUnavailable("fault_service_identity_invalid")
    return service


def _fault_key() -> str:
    return f"{FAULT_KEY_PREFIX}:{_service_name()}"


def _redis_client():
    return redis.Redis.from_url(
        os.environ.get("REDIS_URL", "redis://redis:6379/0"),
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )


def _read_state(*, strict: bool) -> tuple[str, dict] | None:
    try:
        encoded = _redis_client().get(_fault_key())
    except (redis.RedisError, FaultStateUnavailable) as error:
        if strict:
            raise FaultStateUnavailable("fault_state_unavailable") from error
        return None
    if not encoded:
        return None
    try:
        state = json.loads(encoded)
    except (TypeError, json.JSONDecodeError):
        try:
            _redis_client().delete(_fault_key())
        except (redis.RedisError, FaultStateUnavailable):
            pass
        return None
    if state.get("schema_version") != FAULT_SCHEMA_VERSION or state.get("service") != _service_name():
        try:
            _redis_client().delete(_fault_key())
        except (redis.RedisError, FaultStateUnavailable):
            pass
        return None
    return encoded, state


def active_fault() -> dict | None:
    """Return a valid active fault; Redis failure always means normal behaviour."""

    current = _read_state(strict=False)
    if current is None:
        return None
    _, state = current
    if float(state.get("expires_at", 0)) <= time.time():
        try:
            _redis_client().delete(_fault_key())
        except (redis.RedisError, FaultStateUnavailable):
            pass
        return None
    return state


def validate_fault(payload: dict) -> dict:
    scenario = payload.get("scenario")
    duration = int(payload.get("duration_seconds", 0))
    experiment_id = str(payload.get("experiment_id", ""))
    seed = int(payload.get("seed", 0))
    parameters = payload.get("parameters") or {}
    if scenario not in SCENARIOS:
        raise ValueError("fault_scenario_not_allowed")
    if not 15 <= duration <= MAX_DURATION_SECONDS:
        raise ValueError("fault_duration_out_of_range")
    if len(experiment_id) != 36:
        raise ValueError("fault_experiment_id_invalid")
    if not 0 <= seed <= 2_147_483_647:
        raise ValueError("fault_seed_out_of_range")
    allowed_keys = {
        "latency": {"delay_ms"},
        "errors": {"error_probability"},
        "database-slowdown": {"delay_ms"},
        "queue-backlog": {"delay_ms"},
    }[scenario]
    if set(parameters) - allowed_keys:
        raise ValueError("fault_parameter_not_allowed")
    normalized = {key: float(value) for key, value in parameters.items()}
    if "delay_ms" in normalized and not 50 <= normalized["delay_ms"] <= MAX_DELAY_MS:
        raise ValueError("fault_delay_out_of_range")
    if "error_probability" in normalized and not 0.05 <= normalized["error_probability"] <= 1.0:
        raise ValueError("fault_probability_out_of_range")
    return {"scenario": scenario, "duration_seconds": duration, "experiment_id": experiment_id, "seed": seed, "parameters": normalized}


def start_fault(payload: dict) -> dict:
    normalized = validate_fault(payload)
    existing = _read_state(strict=True)
    if existing:
        state = existing[1]
        if state.get("experiment_id") != normalized["experiment_id"]:
            raise ValueError("fault_conflict")
        return state

    now = time.time()
    state = {
        **normalized,
        "schema_version": FAULT_SCHEMA_VERSION,
        "service": _service_name(),
        "started_at": now,
        "expires_at": now + normalized["duration_seconds"],
    }
    encoded = json.dumps(state, sort_keys=True, separators=(",", ":"))
    try:
        created = _redis_client().set(
            _fault_key(),
            encoded,
            ex=max(1, math.ceil(state["expires_at"] - time.time())),
            nx=True,
        )
    except redis.RedisError as error:
        raise FaultStateUnavailable("fault_state_unavailable") from error
    if created:
        return state

    raced = _read_state(strict=True)
    if raced and raced[1].get("experiment_id") == normalized["experiment_id"]:
        return raced[1]
    raise ValueError("fault_conflict")


def stop_fault(experiment_id: str) -> bool:
    current = _read_state(strict=True)
    if current is None:
        return False
    encoded, state = current
    if state.get("experiment_id") != experiment_id:
        raise ValueError("fault_experiment_mismatch")
    script = "if redis.call('get',KEYS[1])==ARGV[1] then return redis.call('del',KEYS[1]) else return 0 end"
    try:
        return bool(_redis_client().eval(script, 1, _fault_key(), encoded))
    except redis.RedisError as error:
        raise FaultStateUnavailable("fault_state_unavailable") from error


def clear_fault_on_startup() -> None:
    """Recover normal service behaviour whenever an API/worker process restarts."""

    try:
        _redis_client().delete(_fault_key())
    except (redis.RedisError, FaultStateUnavailable):
        # Runtime reads also fail open, so Redis downtime cannot inject a fault.
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Enable a bounded local demo fault.")
    parser.add_argument("scenario", choices=SCENARIOS, nargs="?")
    parser.add_argument("--duration", type=int, default=60, choices=range(15, 601))
    parser.add_argument("--experiment-id", default="00000000-0000-0000-0000-000000000000")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--clear", action="store_true")
    args = parser.parse_args()
    if args.clear:
        clear_fault_on_startup()
        return
    if args.scenario is None:
        parser.error("scenario is required unless --clear is used")
    defaults = {"latency": {"delay_ms": 1500}, "errors": {"error_probability": 1.0}, "database-slowdown": {"delay_ms": 750}, "queue-backlog": {"delay_ms": 1500}}
    start_fault({"scenario": args.scenario, "duration_seconds": args.duration, "experiment_id": args.experiment_id, "seed": args.seed, "parameters": defaults[args.scenario]})


if __name__ == "__main__":
    main()
