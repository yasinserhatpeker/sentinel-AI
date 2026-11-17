"""Run bounded, real-service smoke experiments for the four fault scenarios."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from uuid import uuid4

import redis
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from demo.faults import ACTIVE_STATUSES, start_experiment, stop_experiment
from demo.models import FaultExperiment


SCENARIOS = (
    {
        "fault_type": FaultExperiment.FaultType.HIGH_LATENCY,
        "service": "payments-api",
        "url": "http://payments-api:8080/v1/authorizations/",
        "parameters": {"delay_ms": 500},
    },
    {
        "fault_type": FaultExperiment.FaultType.ERROR_BURST,
        "service": "notifications-api",
        "url": "http://notifications-api:8080/v1/notifications/",
        "parameters": {"error_probability": 1.0},
    },
    {
        "fault_type": FaultExperiment.FaultType.DATABASE_SLOWDOWN,
        "service": "inventory-api",
        "url": "http://inventory-api:8080/v1/stock/",
        "parameters": {"delay_ms": 400},
    },
    {
        "fault_type": FaultExperiment.FaultType.QUEUE_BACKLOG,
        "service": "reporting-worker",
        "url": "http://reporting-worker:8080/v1/reports/",
        "parameters": {"delay_ms": 5000},
    },
)


def timed_request(url: str, *, data: dict | None = None) -> dict:
    body = json.dumps(data).encode() if data is not None else None
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"} if body else {},
        method="POST" if body else "GET",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            status = response.status
            response.read()
    except urllib.error.HTTPError as error:
        status = error.code
        error.read()
    return {"status": status, "duration_ms": round((time.perf_counter() - started) * 1000, 1)}


def queued_report_count(url: str) -> int:
    with urllib.request.urlopen(url, timeout=8) as response:
        records = json.loads(response.read())
    return sum(record.get("status") == "queued" for record in records)


class Command(BaseCommand):
    help = "Run all four local-only fault scenarios against real demo-service requests."

    def add_arguments(self, parser):
        parser.add_argument("--duration", type=int, default=15)
        parser.add_argument("--queue-jobs", type=int, default=12)

    def handle(self, *args, **options):
        duration = options["duration"]
        queue_jobs = options["queue_jobs"]
        if not 15 <= duration <= 60:
            raise CommandError("duration must be between 15 and 60 seconds for this smoke command")
        if not 2 <= queue_jobs <= 50:
            raise CommandError("queue-jobs must be between 2 and 50")

        actor = get_user_model().objects.filter(is_active=True, is_superuser=True).order_by("pk").first()
        if actor is None:
            raise CommandError("an active super-admin is required")
        conflicts = FaultExperiment.objects.filter(status__in=ACTIVE_STATUSES)
        if conflicts.exists():
            raise CommandError(f"active/recovering fault experiments must be cleared first: {conflicts.count()}")

        broker = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=1)
        results = []
        for index, scenario in enumerate(SCENARIOS, start=1):
            baseline = timed_request(scenario["url"])
            experiment = start_experiment(
                actor=actor,
                service=scenario["service"],
                fault_type=scenario["fault_type"],
                duration_seconds=duration,
                parameters=scenario["parameters"],
                seed=4200 + index,
            )
            if experiment.status != FaultExperiment.Status.ACTIVE:
                raise CommandError(f"{scenario['fault_type']} failed to start: {experiment.failure_reason}")
            try:
                if scenario["fault_type"] == FaultExperiment.FaultType.QUEUE_BACKLOG:
                    queue_before = int(broker.llen("reporting"))
                    queued_records_before = queued_report_count(scenario["url"])
                    samples = [
                        timed_request(scenario["url"], data={"report_type": f"fault-smoke-{uuid4().hex[:12]}"})
                        for _ in range(queue_jobs)
                    ]
                    time.sleep(0.25)
                    observed = {
                        "request_statuses": sorted({sample["status"] for sample in samples}),
                        "queue_depth_before": queue_before,
                        "queue_depth_during": int(broker.llen("reporting")),
                        "queued_records_before": queued_records_before,
                        "queued_records_during": queued_report_count(scenario["url"]),
                    }
                else:
                    observed = timed_request(scenario["url"])
            finally:
                stopped = stop_experiment(experiment)
            results.append(
                {
                    "fault_type": scenario["fault_type"],
                    "service": scenario["service"],
                    "baseline": baseline,
                    "fault_observation": observed,
                    "experiment_id": str(experiment.pk),
                    "status_after_stop": stopped.status,
                    "ground_truth_windows": stopped.ground_truth_windows.count(),
                }
            )

        self.stdout.write(json.dumps({"schema_version": "fault-smoke.v1", "results": results}, indent=2, sort_keys=True))
