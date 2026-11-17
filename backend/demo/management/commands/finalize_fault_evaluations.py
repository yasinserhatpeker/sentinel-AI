"""Finalize completed telemetry windows and evaluate recent fault experiments."""

from __future__ import annotations

import json
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from demo.detection.baseline import MedianMadDetector, StaticThresholdDetector
from demo.detection.evaluation import evaluate_detector
from demo.detection.sequences import materialize_sequence_journals
from demo.detection.service import score_feature_window
from demo.models import FaultExperiment
from demo.telemetry_ingestion import (
    aggregate_minute,
    completed_minute_start,
    feature_window_start,
    materialize_feature_window,
)


class Command(BaseCommand):
    help = "Aggregate completed windows, score detectors and evaluate recent fault ground truth."

    def add_arguments(self, parser):
        parser.add_argument("--lookback-minutes", type=int, default=30)

    def handle(self, *args, **options):
        lookback = options["lookback_minutes"]
        if not 15 <= lookback <= 24 * 60:
            raise CommandError("lookback-minutes must be between 15 and 1440")

        completed_minute = completed_minute_start()
        aggregate_start = completed_minute - timedelta(minutes=lookback - 1)
        aggregate_count = 0
        cursor = aggregate_start
        while cursor <= completed_minute:
            aggregate_count += aggregate_minute(cursor)
            cursor += timedelta(minutes=1)

        # Subtract one complete feature interval so an in-progress five-minute
        # window is never used by a detector or evaluation.
        latest_feature_start = feature_window_start(timezone.now() - timedelta(minutes=5))
        feature_start = feature_window_start(aggregate_start)
        feature_rows = decision_rows = 0
        cursor = feature_start
        while cursor <= latest_feature_start:
            feature_rows += materialize_feature_window(cursor)
            decision_rows += score_feature_window(cursor)
            cursor += timedelta(minutes=5)

        detectors = (StaticThresholdDetector(), MedianMadDetector())
        experiments = FaultExperiment.objects.filter(
            created_at__gte=aggregate_start,
            status__in=(FaultExperiment.Status.RECOVERING, FaultExperiment.Status.COMPLETED),
        ).order_by("created_at")
        evaluations = []
        services = set()
        for experiment in experiments:
            services.add(experiment.service)
            for detector in detectors:
                result = evaluate_detector(experiment, detector.metadata())
                evaluations.append(
                    {
                        "experiment_id": str(experiment.pk),
                        "fault_type": experiment.fault_type,
                        "service": experiment.service,
                        "detector_type": result.detector_type,
                        "precision": result.precision,
                        "recall": result.recall,
                        "f1_score": result.f1_score,
                        "false_positive_rate": result.false_positive_rate,
                        "detection_delay_seconds": result.detection_delay_seconds,
                    }
                )

        sequence_rows = sum(
            materialize_sequence_journals(environment="local", service=service, sequence_length=12)
            for service in sorted(services)
        )
        self.stdout.write(
            json.dumps(
                {
                    "schema_version": "fault-evaluation-finalize.v1",
                    "completed_minute": completed_minute.isoformat(),
                    "latest_feature_start": latest_feature_start.isoformat(),
                    "aggregate_rows": aggregate_count,
                    "feature_rows": feature_rows,
                    "decision_rows": decision_rows,
                    "sequence_rows": sequence_rows,
                    "evaluations": evaluations,
                },
                indent=2,
                sort_keys=True,
            )
        )
