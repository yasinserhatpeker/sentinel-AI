# Data model and audit rules

- Every persistent model documents ownership, retention and deletion behavior.
- Telemetry rows retain `event_id`, source timestamp, ingestion timestamp and schema version.
- Derived anomalies and incidents retain evidence references and detector/configuration version.
- Mutations that change incident state record actor, reason and correlation ID.
- Sensitive fields are redacted before persistence; retention is enforced by an explicit task.
- Model-state changes require a spec and a reviewed migration plan.
