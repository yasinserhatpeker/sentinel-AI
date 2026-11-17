"""Aggregate-only readiness checks for honest local model training."""

from __future__ import annotations

from datetime import timedelta

from demo.models import SequenceJournal, TelemetryFeature
from demo.telemetry_ingestion import BASE_FEATURE_FIELDS, FEATURE_SCHEMA_V2, FEATURE_V2_NAMES, FEATURE_WINDOW_MINUTES

from .training_data import normal_training_features


ISOLATION_FOREST_MINIMUM_SAMPLES = 50
LSTM_SEQUENCE_LENGTH = 12
LSTM_MINIMUM_SEQUENCES = 60


def _contiguous_run_lengths(windows: list) -> list[int]:
    if not windows:
        return []
    lengths = [1]
    expected_delta = timedelta(minutes=FEATURE_WINDOW_MINUTES)
    for left, right in zip(windows, windows[1:]):
        if right - left == expected_delta:
            lengths[-1] += 1
        elif right != left:
            lengths.append(1)
    return lengths


def model_data_readiness(*, environment: str, service: str, start, end) -> dict:
    rows = list(
        TelemetryFeature.objects.filter(
            schema_version=FEATURE_SCHEMA_V2,
            environment=environment,
            service=service,
            window_start__gte=start,
            window_start__lt=end,
        ).order_by("window_start")
    )
    windows = sorted({row.window_start for row in rows})
    run_lengths = _contiguous_run_lengths(windows)
    longest_run = max(run_lengths, default=0)
    candidate_sequences = sum(max(0, length - LSTM_SEQUENCE_LENGTH + 1) for length in run_lengths)
    expected_between_observations = (
        int((windows[-1] - windows[0]).total_seconds() // (FEATURE_WINDOW_MINUTES * 60)) + 1
        if windows
        else 0
    )
    gap_count = max(0, expected_between_observations - len(windows))

    eligible_training_count = normal_training_features(
        environment=environment,
        service=service,
        start=start,
        end=end,
    ).count()
    total_values = len(rows) * (len(BASE_FEATURE_FIELDS) + len(FEATURE_V2_NAMES))
    missing_values = 0
    for row in rows:
        missing_values += sum(getattr(row, field) is None for field in BASE_FEATURE_FIELDS)
        missing_values += sum(row.feature_values.get(name) is None for name in FEATURE_V2_NAMES)

    journals = SequenceJournal.objects.filter(
        schema_version="sequence.v1",
        environment=environment,
        service=service,
        window_end__gte=start,
        window_end__lt=end,
    )
    split_counts = {
        split: journals.filter(split=split).count()
        for split in (SequenceJournal.Split.TRAIN, SequenceJournal.Split.VALIDATION, SequenceJournal.Split.TEST)
    }
    isolation_ready = eligible_training_count >= ISOLATION_FOREST_MINIMUM_SAMPLES
    lstm_ready = candidate_sequences >= LSTM_MINIMUM_SEQUENCES
    has_partial_data = bool(rows) and (gap_count > 0 or missing_values > 0)
    status = (
        "lstm_ready" if lstm_ready
        else "isolation_forest_ready" if isolation_ready
        else "partial" if has_partial_data
        else "collecting"
    )
    required_feature_windows = LSTM_MINIMUM_SEQUENCES + LSTM_SEQUENCE_LENGTH - 1
    remaining_windows = max(0, required_feature_windows - longest_run)

    return {
        "schema_version": "model-readiness.v1",
        "scope": {"environment": environment, "service": service, "start": start, "end": end},
        "status": status,
        "feature_sample_count": len(rows),
        "eligible_isolation_forest_sample_count": eligible_training_count,
        "isolation_forest_minimum_samples": ISOLATION_FOREST_MINIMUM_SAMPLES,
        "isolation_forest_ready": isolation_ready,
        "first_window": windows[0] if windows else None,
        "last_window": windows[-1] if windows else None,
        "longest_contiguous_window_count": longest_run,
        "sequence_gap_count": gap_count,
        "missing_value_count": missing_values,
        "missing_value_ratio": (missing_values / total_values) if total_values else None,
        "sequence_length": LSTM_SEQUENCE_LENGTH,
        "candidate_sequence_count": candidate_sequences,
        "materialized_sequence_count": journals.count(),
        "sequence_split_counts": split_counts,
        "lstm_minimum_sequences": LSTM_MINIMUM_SEQUENCES,
        "lstm_ready": lstm_ready,
        "windows_remaining_for_lstm": remaining_windows,
        "estimated_minutes_remaining_for_lstm": remaining_windows * FEATURE_WINDOW_MINUTES,
    }
