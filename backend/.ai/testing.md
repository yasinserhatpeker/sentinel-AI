# Backend testing rules

- Test the ingestion contract, normalization, duplicate delivery and task retry behavior.
- Test aggregation boundaries with fixed UTC timestamps and deterministic fixtures.
- Test detector results against known normal, anomalous and noisy samples.
- Test query scope and malformed filter denial; do not mock the behavior under test.
- Record command output and baseline limitations in the active spec tasks file.
