# Backend conventions

- Use Django REST Framework for HTTP-facing APIs and keep serializers, views and URLs explicit.
- Keep ingestion validation separate from normalization, persistence and asynchronous processing.
- Use bounded payloads, stable identifiers, UTC timestamps and versioned contracts.
- Make Celery tasks idempotent, retry-safe and safe to run out of order.
- Do not call an LLM from a synchronous ingestion path.
- Log correlation IDs and bounded metadata only; never log secrets or unredacted sensitive payloads.
- Add tests for valid input, malformed input, duplicate delivery, retries and scope filters.
- API, model, task or schema changes require an active spec before implementation.
