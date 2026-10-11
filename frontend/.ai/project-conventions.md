# Frontend conventions

- Use Vue 3, TypeScript, Composition API and the existing component system.
- Keep domain modules separate: telemetry, anomalies, incidents and analysis.
- Keep API types and services aligned with the backend contract.
- Every live view needs loading, empty, partial-data and error states.
- Charts expose time range, environment and service context.
- AI output displays evidence references, model/version and confidence; it is advisory.
- New routes, shared stores, services or chart abstractions require a spec.
