"""Create deterministic local aggregate telemetry for the dashboard walkthrough."""

from __future__ import annotations

from datetime import UTC, timedelta
from uuid import NAMESPACE_URL, uuid5

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from demo.telemetry_ingestion import aggregate_minute, persist_metric_events


class Command(BaseCommand):
    help = "Seed deterministic local telemetry for the SentinelAI dashboard."

    def add_arguments(self, parser):
        parser.add_argument("--minutes", type=int, default=30)
        parser.add_argument("--service", default="sentinel-demo-api")

    def handle(self, *args, **options):
        minutes = options["minutes"]
        if not 5 <= minutes <= 120:
            raise CommandError("minutes_must_be_between_5_and_120")

        service = options["service"]
        end = timezone.now().astimezone(UTC).replace(second=0, microsecond=0)
        start = end - timedelta(minutes=minutes)
        metrics = (
            ("http.server.request_count", "count", lambda index: 18 + (index % 7)),
            ("http.server.error_rate", "percent", lambda index: 1.0 if index % 9 else 4.5),
            ("http.server.duration", "ms", lambda index: 95 + ((index * 13) % 70)),
            ("runtime.cpu.usage", "percent", lambda index: 32 + ((index * 7) % 38)),
            ("runtime.memory.usage", "percent", lambda index: 47 + ((index * 3) % 23)),
            ("db.connection.usage", "count", lambda index: 4 + (index % 5)),
            ("db.query.duration", "ms", lambda index: 12 + ((index * 5) % 24)),
            ("db.query.errors", "count", lambda index: 1 if index % 17 == 0 else 0),
            ("queue.depth", "count", lambda index: 2 + ((index * 3) % 14)),
            ("queue.oldest_message_age", "s", lambda index: 4 + ((index * 11) % 40)),
            ("queue.enqueue_rate", "per_s", lambda index: 2 + (index % 4)),
            ("queue.dequeue_rate", "per_s", lambda index: 2 + ((index + 1) % 4)),
            ("queue.failed_task_count", "count", lambda index: 1 if index % 13 == 0 else 0),
        )
        events = []
        for index in range(minutes):
            observed_at = start + timedelta(minutes=index, seconds=30)
            for metric_name, unit, value_factory in metrics:
                events.append(
                    {
                        "event_id": uuid5(
                            NAMESPACE_URL,
                            f"sentinel-dashboard/{service}/{observed_at.isoformat()}/{metric_name}",
                        ),
                        "observed_at": observed_at,
                        "metric": {"name": metric_name, "value": float(value_factory(index)), "unit": unit},
                        "context": {
                            "environment": "local",
                            "service": service,
                            "instance": "api-1",
                            "deployment_id": "local-demo",
                        },
                        "dimensions": {"source": "dashboard-seed"},
                    }
                )
        inserted, duplicates = persist_metric_events(events)
        aggregate_count = sum(aggregate_minute(start + timedelta(minutes=index)) for index in range(minutes))
        self.stdout.write(
            self.style.SUCCESS(
                f"dashboard_telemetry_seeded inserted={inserted} duplicates={duplicates} aggregates={aggregate_count}"
            )
        )
