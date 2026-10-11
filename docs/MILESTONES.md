# SentinelAI milestones

The dates and deliverables below are extracted from the supplied project report. They
are project requirements, not instructions that override the user's implementation request.

| Date | Milestone | Deliverable |
|---|---|---|
| 15.10.2026 | Research, requirements analysis and system design | Scope, data flow, telemetry model, architecture boundaries, minimum metrics and fault-injection scenarios |
| 29.10.2026 | Telemetry infrastructure, demo system and dashboard foundation | Demo app, HTTP/queue/runtime/database collection, ingestion API, aggregation and first Vue dashboard |
| 12.11.2026 | Anomaly detection and fault-injection experiments | Threshold/statistical baseline, Isolation Forest, controlled faults and precision/recall/F1/false-positive/delay results |
| 03.12.2026 | Incident correlation and AI-assisted root-cause analysis | Time/service correlation, incident timeline, structured context, hypotheses, evidence and investigation steps |
| 24.12.2026 | Integration, testing, success analysis and final presentation | End-to-end integration, scenario-based evaluation, limitations, demo, technical documentation and result tables |

## Implementation order

The sequence is intentionally dependency-driven: define contracts first, collect and
aggregate telemetry second, detect anomalies third, correlate incidents fourth, and only
then add LLM-assisted explanation and final evaluation.
