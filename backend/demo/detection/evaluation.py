"""Ground-truth evaluation for traceable detector decisions."""

from __future__ import annotations

from .base import DetectorMetadata
from .baseline import MedianMadDetector, StaticThresholdDetector
from demo.models import DetectionDecision, DetectorEvaluation, FaultExperiment, GroundTruthWindow


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def detector_metadata_for_experiment(experiment: FaultExperiment) -> tuple[DetectorMetadata, ...]:
    """Return baselines plus model versions with real decisions in labelled windows."""

    label_windows = experiment.ground_truth_windows.values("window_start")
    model_metadata = {
        DetectorMetadata(
            detector_type=detector_type,
            detector_version=detector_version,
            configuration_version=configuration_version,
            model_version=model_version,
        )
        for detector_type, detector_version, configuration_version, model_version in DetectionDecision.objects.filter(
            environment=experiment.environment,
            service=experiment.service,
            detector_type="isolation_forest",
            feature__window_start__in=label_windows,
        ).values_list("detector_type", "detector_version", "configuration_version", "model_version")
        if model_version
    }
    return (
        StaticThresholdDetector().metadata(),
        MedianMadDetector().metadata(),
        *sorted(model_metadata, key=lambda item: item.model_version),
    )


def evaluate_experiments_for_window(window_start) -> int:
    """Refresh evaluations whose labelled evidence includes a completed window."""

    experiments = FaultExperiment.objects.filter(
        status__in=(FaultExperiment.Status.RECOVERING, FaultExperiment.Status.COMPLETED),
        ground_truth_windows__window_start=window_start,
    ).distinct()
    evaluation_count = 0
    for experiment in experiments:
        for metadata in detector_metadata_for_experiment(experiment):
            evaluate_detector(experiment, metadata)
            evaluation_count += 1
    return evaluation_count


def evaluate_detector(experiment: FaultExperiment, metadata: DetectorMetadata) -> DetectorEvaluation:
    labels = list(experiment.ground_truth_windows.order_by("window_start"))
    if not labels:
        raise ValueError("evaluation_ground_truth_missing")
    decisions = {
        decision.feature.window_start: decision
        for decision in DetectionDecision.objects.filter(
            environment=experiment.environment,
            service=experiment.service,
            detector_type=metadata.detector_type,
            detector_version=metadata.detector_version,
            configuration_version=metadata.configuration_version,
            model_version=metadata.model_version,
            feature__window_start__in=[label.window_start for label in labels],
        ).select_related("feature")
    }
    tp = fp = tn = fn = 0
    for label in labels:
        decision = decisions.get(label.window_start)
        predicted = bool(decision and decision.is_anomaly)
        if label.label == GroundTruthWindow.Label.FAULT_ACTIVE:
            if predicted:
                tp += 1
            else:
                fn += 1
        elif label.label == GroundTruthWindow.Label.NORMAL:
            if predicted:
                fp += 1
            else:
                tn += 1

    precision = _safe_ratio(tp, tp + fp)
    recall = _safe_ratio(tp, tp + fn)
    first_fault = next((label for label in labels if label.label == GroundTruthWindow.Label.FAULT_ACTIVE), None)
    first_detection = next((decisions.get(label.window_start) for label in labels if label.label == GroundTruthWindow.Label.FAULT_ACTIVE and decisions.get(label.window_start) and decisions[label.window_start].is_anomaly), None)
    first_recovery = next((label for label in labels if label.label == GroundTruthWindow.Label.RECOVERING), None)
    first_normal_decision = next((decisions.get(label.window_start) for label in labels if label.label == GroundTruthWindow.Label.RECOVERING and decisions.get(label.window_start) and not decisions[label.window_start].is_anomaly), None)
    detection_delay = None
    if first_fault and first_detection:
        detection_delay = max(0.0, (first_detection.feature.window_start - first_fault.window_start).total_seconds())
    recovery_delay = None
    if first_recovery and first_normal_decision:
        recovery_delay = max(0.0, (first_normal_decision.feature.window_start - first_recovery.window_start).total_seconds())
    evaluation, _ = DetectorEvaluation.objects.update_or_create(
        experiment=experiment,
        detector_type=metadata.detector_type,
        detector_version=metadata.detector_version,
        configuration_version=metadata.configuration_version,
        model_version=metadata.model_version,
        defaults={
            "true_positive": tp, "false_positive": fp, "true_negative": tn, "false_negative": fn,
            "precision": precision, "recall": recall,
            "f1_score": _safe_ratio(2 * precision * recall, precision + recall),
            "false_positive_rate": _safe_ratio(fp, fp + tn),
            "detection_delay_seconds": detection_delay,
            "recovery_delay_seconds": recovery_delay,
        },
    )
    return evaluation
