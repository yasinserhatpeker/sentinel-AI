"""Leakage-safe ordered sequence journals and a gated offline LSTM prototype."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import warnings

import numpy as np

from demo.models import GroundTruthWindow, SequenceJournal, TelemetryFeature
from demo.telemetry_ingestion import FEATURE_SCHEMA_V2, FEATURE_WINDOW_MINUTES

from .isolation_forest import MODEL_FEATURE_NAMES, feature_vector


SEQUENCE_SCHEMA_VERSION = "sequence.v1"


def materialize_sequence_journals(*, environment: str, service: str, sequence_length: int = 12, start=None, end=None) -> int:
    if not 2 <= sequence_length <= 288:
        raise ValueError("sequence_length_out_of_range")
    row_query = TelemetryFeature.objects.filter(schema_version=FEATURE_SCHEMA_V2, environment=environment, service=service)
    label_query = GroundTruthWindow.objects.filter(environment=environment, service=service)
    if start is not None:
        row_query = row_query.filter(window_start__gte=start)
        label_query = label_query.filter(window_start__gte=start)
    if end is not None:
        row_query = row_query.filter(window_start__lt=end)
        label_query = label_query.filter(window_start__lt=end)
    rows = list(row_query.order_by("window_start"))
    candidates: list[tuple[list[TelemetryFeature], bool]] = []
    labels = {label.window_start: label.label for label in label_query}
    for index in range(sequence_length - 1, len(rows)):
        sequence = rows[index - sequence_length + 1:index + 1]
        contiguous = all(right.window_start - left.window_start == timedelta(minutes=FEATURE_WINDOW_MINUTES) for left, right in zip(sequence, sequence[1:]))
        if not contiguous:
            continue
        candidates.append((sequence, labels.get(sequence[-1].window_start) == GroundTruthWindow.Label.FAULT_ACTIVE))
    train_end = int(len(candidates) * 0.70)
    validation_end = int(len(candidates) * 0.85)
    for index, (sequence, target) in enumerate(candidates):
        split = SequenceJournal.Split.TRAIN if index < train_end else SequenceJournal.Split.VALIDATION if index < validation_end else SequenceJournal.Split.TEST
        SequenceJournal.objects.update_or_create(
            schema_version=SEQUENCE_SCHEMA_VERSION,
            environment=environment,
            service=service,
            window_end=sequence[-1].window_start,
            defaults={"sequence_length": sequence_length, "feature_ids": [row.pk for row in sequence], "target_is_anomaly": target, "split": split},
        )
    return len(candidates)


def _journal_tensor(journals: list[SequenceJournal]) -> tuple[np.ndarray, np.ndarray]:
    tensors = []
    targets = []
    for journal in journals:
        rows = {row.pk: row for row in TelemetryFeature.objects.filter(pk__in=journal.feature_ids)}
        ordered = [rows[feature_id] for feature_id in journal.feature_ids]
        tensors.append([feature_vector(row) for row in ordered])
        targets.append(float(journal.target_is_anomaly))
    return np.asarray(tensors, dtype=float), np.asarray(targets, dtype=float)


@dataclass(frozen=True)
class LstmPrototypeResult:
    train_samples: int
    validation_samples: int
    test_samples: int
    validation_accuracy: float
    test_accuracy: float


def train_lstm_prototype(*, environment: str, service: str, minimum_sequences: int = 60, epochs: int = 25, seed: int = 42, start=None, end=None) -> LstmPrototypeResult:
    """Train a small deterministic NumPy LSTM encoder plus logistic readout offline."""

    journal_query = SequenceJournal.objects.filter(schema_version=SEQUENCE_SCHEMA_VERSION, environment=environment, service=service)
    if start is not None:
        journal_query = journal_query.filter(window_end__gte=start)
    if end is not None:
        journal_query = journal_query.filter(window_end__lt=end)
    journals = list(journal_query.order_by("window_end"))
    if len(journals) < minimum_sequences:
        raise ValueError("lstm_minimum_sequences_not_met")
    train = [item for item in journals if item.split == SequenceJournal.Split.TRAIN]
    validation = [item for item in journals if item.split == SequenceJournal.Split.VALIDATION]
    test = [item for item in journals if item.split == SequenceJournal.Split.TEST]
    if not train or not validation or not test:
        raise ValueError("lstm_split_incomplete")
    x_train, y_train = _journal_tensor(train)
    x_validation, y_validation = _journal_tensor(validation)
    x_test, y_test = _journal_tensor(test)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        medians = np.nanmedian(x_train, axis=(0, 1))
        scales = np.nanstd(x_train, axis=(0, 1))
    medians = np.where(np.isnan(medians), 0.0, medians)
    scales = np.where((np.isnan(scales)) | (scales == 0), 1.0, scales)

    def prepare(values):
        return (np.where(np.isnan(values), medians, values) - medians) / scales

    x_train, x_validation, x_test = prepare(x_train), prepare(x_validation), prepare(x_test)
    rng = np.random.default_rng(seed)
    input_size = x_train.shape[2]
    hidden_size = min(12, max(4, input_size // 16))
    recurrent = rng.normal(0, 0.08, size=(input_size + hidden_size, hidden_size * 4))
    bias = np.zeros(hidden_size * 4)

    def encode(batch):
        hidden = np.zeros((len(batch), hidden_size))
        cell = np.zeros_like(hidden)
        for step in range(batch.shape[1]):
            gates = np.concatenate((batch[:, step, :], hidden), axis=1) @ recurrent + bias
            incoming, forget, candidate, output = np.split(gates, 4, axis=1)
            incoming = 1 / (1 + np.exp(-np.clip(incoming, -30, 30)))
            forget = 1 / (1 + np.exp(-np.clip(forget, -30, 30)))
            output = 1 / (1 + np.exp(-np.clip(output, -30, 30)))
            candidate = np.tanh(candidate)
            cell = forget * cell + incoming * candidate
            hidden = output * np.tanh(cell)
        return hidden

    train_encoded = encode(x_train)
    validation_encoded = encode(x_validation)
    test_encoded = encode(x_test)
    weights = np.zeros(hidden_size)
    output_bias = 0.0
    for _ in range(max(1, min(epochs, 200))):
        logits = train_encoded @ weights + output_bias
        probabilities = 1 / (1 + np.exp(-np.clip(logits, -30, 30)))
        error = probabilities - y_train
        weights -= 0.1 * (train_encoded.T @ error / len(train_encoded))
        output_bias -= 0.1 * float(np.mean(error))

    def accuracy(encoded, targets):
        predictions = (1 / (1 + np.exp(-np.clip(encoded @ weights + output_bias, -30, 30))) >= 0.5)
        return float(np.mean(predictions == targets))

    return LstmPrototypeResult(len(train), len(validation), len(test), accuracy(validation_encoded, y_validation), accuracy(test_encoded, y_test))
