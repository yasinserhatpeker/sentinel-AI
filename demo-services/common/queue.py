"""Real Redis queue observations shared by local demo service workers."""

from __future__ import annotations

import os
import uuid

import redis
from django.conf import settings

from .telemetry import publish_measurements


def publish_queue_event(queue: str, outcome: str, measurements: list[tuple[str, float, str]]) -> None:
    """Add the current broker depth when Redis is reachable; never invent it."""
    measured = list(measurements)
    try:
        client = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=1)
        measured.append(("queue.depth", float(client.llen(queue)), "messages"))
    except redis.RedisError:
        pass
    service = os.environ.get("SENTINEL_SERVICE_NAME", "unknown-service")
    publish_measurements(service, uuid.uuid4().hex, measured, {"queue": queue, "outcome": outcome})
