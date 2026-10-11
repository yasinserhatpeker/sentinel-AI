# Query and visibility rules

- A query must make its environment, service and time-range scope visible in code.
- Default to the narrowest requested scope; do not widen a query because a filter is absent.
- Incident evidence must only reference records visible in the same analysis scope.
- Administrative or cross-environment views require an explicit permission decision in the spec.
- Add denial tests for an out-of-scope environment, service and time range.
