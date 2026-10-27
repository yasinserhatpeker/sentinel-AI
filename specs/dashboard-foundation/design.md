---
slug: dashboard-foundation
title: Local telemetry dashboard foundation
author: Yasin Serhat Peker
area: frontend
status: active
created: 2026-10-27 14:10
updated: 2026-10-27 14:39
---

# Design — Local telemetry dashboard foundation

## Approach

Create a small Vue 3 + TypeScript dashboard under `frontend/`, using the Composition API
and typed API view models. It will be served locally through a Docker Compose service and
will talk directly to the local Django API. A local super-admin signs in with their username or
email and password. The short-lived access JWT remains in reactive in-memory state, while the
rotating refresh JWT is an `HttpOnly` cookie; neither is placed in local storage, a URL, source
file, analytics payload or committed environment file.

The backend adds read-only `telemetry.v1` service-discovery and aggregate endpoints. Every
aggregate request must specify `environment`, `service`, `start`, and `end`; the API applies
a bounded maximum range and returns a stable envelope with series metadata, minute points
and data-availability information. The dashboard uses that contract to render service
health cards and chart groups. It must distinguish a request failure from no telemetry and
from partial metric coverage.

The dashboard visual language is a restrained corporate observability interface: forest and
emerald green establish product identity, while neutral slate, white and muted status colours
keep telemetry legible. It uses an Inter/system sans-serif stack, a persistent desktop sidebar,
a compact scope bar and dense, well-spaced panels. Corners, borders and motion remain subtle;
there are no decorative AI illustrations, generative-looking gradients, mascot imagery or
unrelated iconography. Icons, where useful, are small familiar functional SVGs accompanied by
text labels or accessible names. Status never relies on colour alone.

For the local walkthrough, real requests to the five demo service APIs and report jobs produce
the metric events. The dashboard never invents measurements: unavailable metric groups render an
explicit partial-data state. Native OTLP-to-storage forwarding remains separate from this
dashboard contract.

## Blocking decisions

### Data ownership and retention

- Status: `confirmed: dashboard queries existing local aggregates derived from real demo-service
  activity; no new persisted dashboard model is planned.`
- Raw-event 30-day retention and aggregate retention remain unchanged.
- Migration required: no, unless implementation discovers an indispensable additive index;
  any such need will be recorded and generated only in local Docker, never committed.

### Authentication and query visibility

- Status: `confirmed: a local Django super-admin signs in per browser session. Read requests use
  an in-memory Bearer access JWT; scope always includes explicit environment, service and UTC
  start/end timestamps. Dashboard defaults are visible and may be changed by the user.`
- Denial behaviour: missing/invalid JWT, omitted scope, malformed timestamps, unknown
  service, and a range exceeding the documented maximum receive stable denial responses;
  the UI renders a safe error state without exposing the token.

### Mutation, audit and logging

- Status: `not_applicable: the dashboard and its new backend endpoints are read-only.`
- State-changing paths: none; demo domain requests happen outside the dashboard and are not a
  dashboard side effect.
- Audit and safe logging decision: client errors log only bounded status/code metadata;
  no token, raw event payload or sensitive dimension is rendered or logged.

### Telemetry contract and privacy

- Status: `confirmed: the read contract exposes aggregate values and safe dimensions only, never raw
  payloads. It uses `telemetry.v1` scope/context names and returns metric availability per
  group. The chart contract is versioned alongside the backend response serializer.
- Redaction and external-egress decision: all data remains in local Docker; no LLM, remote
  analytics, external telemetry provider or production data is used.

### Operational safety

- Status: `confirmed: the frontend is a local Compose service; API time ranges are bounded to avoid
  unbounded aggregate queries; the dashboard has no mutation/fault-control action; Compose
  teardown removes local resources. CI adds frontend build validation and retains backend
  integration checks.

### Interface direction

- Status: `confirmed: corporate green local operations dashboard; no decorative AI-style UI.`
- Palette: forest `#123C32`, primary emerald `#167A58`, pale green surface `#EAF6F0`, and
  neutral slate surfaces/text. Amber and red are reserved for warning/error states and meet
  contrast requirements with adjacent text.
- Layout: a stable approximately 240 px navigation rail on large screens; a top context bar;
  then explicit environment, service and time-range controls before health summaries and chart
  panels. The layout collapses accessibly on narrower displays without hiding scope context.
- Components: compact controls, restrained 8–12 px radii, thin neutral borders, clear table
  and chart labels, and no floating decorative cards. Interactive state changes use short
  transitions (about 150–200 ms) and honour `prefers-reduced-motion`.

## Probe findings

- `docs/MILESTONES.md` — the 29 October milestone explicitly includes the first Vue
  dashboard after telemetry ingestion and aggregation.
- `docs/demo-services-and-data-collection.md` — first views require service status, time
  range and basic metric charts; controlled faults and detection are later work.
- `frontend/.ai/frontend-ai-rules.md` — every live view requires loading, empty,
  partial-data and error states; secrets cannot live in local storage or URLs.
- `frontend/.ai/project-conventions.md` — Vue 3, TypeScript, Composition API, typed view
  models, explicit context and separate domain modules are required.
- `backend/.ai/queryset-authorization.md` — telemetry queries must visibly scope
  environment, service and time range.
- `specs/archive/2026-10-18-telemetry-ingestion/` — the existing writer/aggregate contract
  is the dashboard's data source and has no public read endpoint yet.

## Rejected alternatives

| Option | Why not |
|---|---|
| Put a JWT or machine credential in `VITE_*` configuration | Browser build variables are exposed to users and are not a safe secret store. |
| Fetch unscoped aggregate data then filter in Vue | Widens data visibility and increases query cost; scope must be enforced by the API. |
| Render fabricated zero-valued charts for missing series | Misrepresents coverage and can mislead later anomaly evaluation. |
| Add anomaly/incident screens now | Detection, correlation and incident contracts belong to later milestones. |
| Parse native OTLP in the dashboard | UI must consume a stable application API, not transport-specific telemetry payloads. |
| Use generic glowing "AI" decoration or novelty icons | It would obscure operational information and does not fit a sober monitoring product. |

## API and data contract

- Endpoint(s): JWT-protected local service discovery under `/api/telemetry/v1/` and a
  JWT-protected aggregate read endpoint with required environment/service/start/end query
  parameters; exact route names, serializer fields and max range are frozen in tests.
- Event/schema fields: aggregate window, metric identifier/unit, scope context, count,
  min/max/average/last/p50/p95/p99, plus availability metadata. No raw event payload is
  returned to the dashboard.
- Query parameters and response shape: all query context is explicit; UTC ISO-8601 time
  range; consistent empty response versus stable error response.
- Compatibility: existing ingestion routes and demo order API retain their behaviour.

## Impact analysis

- Changed: local Docker topology, backend read API, frontend source tree, CI validation and
  operator-facing local workflow.
- Possibly affected: upcoming anomaly, incident and fault modules consume the same scope and
  aggregate contract.
- Risk: dashboard appears empty without real local demo-service activity; date/time and
  scope mismatch can confuse users; chart libraries increase build complexity.
- Recommendation: preserve the JWT login and four metric groups, then evolve the typed dashboard
  and read contract before expanding charts or adding fault controls.

## Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-10-27 | Use short-lived in-memory access JWT with rotating `HttpOnly` refresh cookie | It supports authenticated local super-admin access without persistent browser token storage. |
| 2026-10-27 | Require environment/service/time scope on all aggregate reads | It follows the project visibility invariant and keeps queries bounded. |
| 2026-10-27 | Treat unavailable metric groups as partial data | Dashboard must not create false operational confidence from fabricated zeros. |
| 2026-10-27 | Use restrained forest/emerald visual tokens and functional icons only | The interface should feel like a credible internal operations product, not a decorative AI demo. |

## Rules consulted

- `AGENTS.md`
- `specs/README.md`
- `backend/.ai/backend-conventions.md`
- `backend/.ai/drf-viewsets.md`
- `backend/.ai/queryset-authorization.md`
- `backend/.ai/testing.md`
- `frontend/.ai/README.md`
- `frontend/.ai/frontend-ai-rules.md`
- `frontend/.ai/project-conventions.md`
