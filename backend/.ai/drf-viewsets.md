# API and endpoint rules

- Define authentication and permission behavior explicitly for every endpoint.
- Validate event size, required dimensions, timestamp range and schema version at the boundary.
- Return stable error shapes without stack traces, secrets or raw internal exceptions.
- Scope every query by environment, service and requested time range where applicable.
- Keep request/response examples and frontend types synchronized with the API contract.
- New endpoints, actions or contract changes require a spec and contract tests.
