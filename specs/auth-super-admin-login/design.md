---
slug: auth-super-admin-login
title: Local super-admin JWT authentication
author: Yasin Serhat Peker
area: backend
status: active
created: 2026-10-27 15:35
updated: 2026-10-27 16:05
---

# Design — Local super-admin JWT authentication

## Approach

Django does not provide a built-in JWT implementation. SentinelAI will keep Django's built-in
authentication model and password facilities, set `BCryptSHA256PasswordHasher` as the preferred
password hasher, and use `djangorestframework-simplejwt` for standards-based access/refresh token
issuance and validation. This avoids inventing a cryptographic token implementation.

Each developer creates one or more local accounts with Django's standard `createsuperuser`
workflow. A local developer database is intentionally independent: a contributor creates their
own account after starting Compose, and credentials never appear in environment configuration,
source, fixtures, logs or API responses. Login accepts only active users with `is_superuser=True`.
Django's built-in `User` model remains sufficient; no model change or source migration is planned.

`POST /api/auth/login/` accepts bounded `identifier` (username or email) and `password` fields, authenticates an active
super-admin and returns a short-lived access JWT while setting a rotating refresh JWT in a
local `HttpOnly`, `SameSite=Lax` cookie. SimpleJWT's token-blacklist application records issued
refresh tokens in the database and invalidates rotated/revoked tokens. The API uses
`JWTAuthentication` for protected routes. The Vue login form keeps only the access token in
reactive memory; a page refresh calls the refresh endpoint, which reads the cookie and restores
the short-lived access token. Logout blacklists the active refresh token, clears the cookie and
returns to the login state.

## Security baseline

This is an OWASP-aligned application baseline, not a claim that a local HTTP-only Docker demo can
provide every production infrastructure control. The implementation will apply the following
controls within SentinelAI's application boundary:

- `HttpOnly; SameSite=Lax; Path=/api/auth/` refresh cookie; `Secure` is enabled whenever Django
  does not run in local debug mode. Local HTTP uses a non-`Secure` cookie only because browsers
  otherwise reject it. A `__Host-` prefix remains a future HTTPS-deployment concern because it
  requires `Path=/` while this local cookie is intentionally scoped to `/api/auth/`.
- Django CSRF token validation for cookie-authenticated login, refresh and logout requests; Vue
  obtains the CSRF cookie from a dedicated endpoint and sends `X-CSRFToken`. Server checks
  `Origin`/`Referer` and rejects unsafe cross-site Fetch Metadata where available. SameSite is
  defence in depth, not the only CSRF control.
- Refresh rotation plus blacklist-on-rotation/logout; short access lifetime; separate
  `JWT_SIGNING_KEY` environment secret; issuer/audience validation and JTI identifiers.
- Bcrypt SHA-256 password hashing, Django password validation (minimum length, common-password,
  numeric-only and user-attribute similarity checks), generic login failures and cache-backed
  login throttling keyed by a one-way digest of source/IP and submitted identifier.
- No credentials, JWTs, CSRF tokens or raw authorization headers in UI, URLs, logs, telemetry or
  API error responses. Vue uses escaped template bindings; `v-html` is prohibited for auth data.
- Restrictive CSP, `X-Content-Type-Options: nosniff`, frame-ancestor/clickjacking defence,
  Referrer-Policy, Permissions-Policy and no-store cache headers for login/auth responses.
- Same-origin local Vite proxy only; no permissive CORS. Dependency and configuration checks are
  added to CI where practical.

## Blocking decisions

### Data ownership and retention

- Status: `confirmed: Django's existing built-in auth tables hold one or more local super-admin accounts.`
  No new application model or committed migration is needed; local Docker may create built-in
  Django migrations in its named volume.
- Credentials source: each developer enters credentials interactively into Django's standard
  `createsuperuser` command. They are not environment variables, spec examples, fixtures, logs or
  source values.

### Authentication and query visibility

- Status: `confirmed: one or more local super-admins sign in by email/password and receive a short-lived
  access JWT plus a rotating refresh JWT. Login explicitly requires `is_active` and
  `is_superuser`; staff-only or ordinary accounts receive the same generic denial. The refresh JWT
  is persisted as an outstanding/revocable token in the SimpleJWT database and is sent only as a
  local HttpOnly cookie; JavaScript cannot read it. All protected routes require `Bearer`
  authentication; health remains public. Dashboard telemetry scope remains explicit after
  authentication.
- Denial behaviour: malformed input and invalid credentials return the same stable login denial;
  absent/invalid/expired access tokens produce a stable authentication denial without exposing a
  password, account status or token payload.

### Mutation, audit and logging

- Status: `confirmed`
- State-changing paths: Django's interactive superuser command creates local accounts; login,
  refresh and logout only affect bounded authentication-token state.
- Audit and safe logging decision: no raw `Authorization` header, credential or login body
  appears in API errors or logs.

### Telemetry contract and privacy

- Status: `not_applicable: authentication changes access control only and introduces no telemetry schema or external egress.`

### Operational safety

- Status: `confirmed: there is no account bootstrap at API startup; access and refresh lifetimes are
  bounded; JWT signing uses a separate environment secret; rate limits use Redis; cookie/header
  security is tested. The refresh cookie is not marked `Secure` only because this is explicit HTTP
  local Docker development. Rollback removes the auth configuration only by an explicit code
  change.

## Probe findings

- `backend/config/settings.py` — all protected routes currently use the custom shared demo-token
  authentication class.
- the former custom demo-token principal was non-persistent and had no email identity, so it was
  removed rather than retained as a parallel access path.
- `backend/requirements.txt` — Django and DRF exist; JWT and bcrypt dependencies do not yet.
- `frontend/src/App.vue` — current dashboard token is memory-only, making the intended JWT
  storage boundary straightforward to retain.
- `AGENTS.md` — migrations must not be generated or committed; credentials cannot enter source,
  specs or logs.

## Rejected alternatives

| Option | Why not |
|---|---|
| Implement JWT signing/verification directly | Security-sensitive cryptography should use a maintained library. |
| Store refresh JWTs in local storage | It makes browser token theft and accidental persistence more likely. |
| Rely on SameSite alone for CSRF | SameSite is defence in depth; unsafe cookie requests need explicit CSRF and origin controls. |
| Write custom rate limiting or JWT cryptography | Maintained Django/DRF/Redis primitives reduce security-sensitive bespoke code. |
| Keep the shared demo token alongside JWT | It leaves a weaker, anonymous access path. |
| Create a custom user model now | It requires a broader identity migration; the built-in user supports multiple local super-admins. |
| Use Django session cookies | The requested API model is JWT-based and the SPA needs a simple local Bearer contract. |

## API and data contract

- Endpoint(s): `POST /api/auth/login/` and a bounded JWT refresh route under `/api/auth/`.
- Login input: username-or-email identifier (maximum 254 characters) and password (maximum 128 characters); no password
  is echoed. Success returns an access token and sets an HttpOnly refresh cookie; denial returns
  the stable code `invalid_credentials`. Refresh rotates the database-backed token and returns a
  new access token without exposing the refresh token to JavaScript.
- Protected routes: existing order and telemetry endpoints move from `Authorization: Demo ...` to
  `Authorization: Bearer <access-token>`.
- Compatibility: the old demo-token header is intentionally removed after approval; API docs and
  dashboard types change together.

## Impact analysis

- Changed: local API access, dashboard entry screen, CI test setup and local operator walkthrough.
- Possibly affected: every existing protected API test and future service clients.
- Risk: a weak local super-admin password would undermine the local demo; local HTTP cannot set a
  production `Secure` cookie. Each contributor must initialize their own local user before login.
- Recommendation: approve the multiple-super-admin policy and database-backed refresh-session boundary, then
  implement authentication before considering the dashboard milestone fully closed.

## Decision log

| Date | Decision | Why |
|---|---|---|
| 2026-10-27 | Use Django built-in users plus BCryptSHA256PasswordHasher | Provides a familiar maintained password path without a custom-user migration. |
| 2026-10-27 | Use djangorestframework-simplejwt for JWTs | Django has no built-in JWT library; a maintained DRF integration avoids custom cryptography. |
| 2026-10-27 | Use a database-backed rotating refresh token with an HttpOnly local cookie | Keeps the session across refresh without exposing the refresh token to JavaScript. |
| 2026-10-27 | Apply an OWASP-aligned auth/web baseline | Cookie flags alone do not cover CSRF, XSS, throttling, security headers or token revocation. |
| 2026-10-27 | Create local accounts with `createsuperuser`, allowing multiple super-admins | Credentials stay outside environment files and every contributor can initialize their own local account. |

## Rules consulted

- `AGENTS.md`
- `specs/README.md`
- `backend/.ai/backend-conventions.md`
- `backend/.ai/drf-viewsets.md`
- `backend/.ai/queryset-authorization.md`
- `backend/.ai/testing.md`
- `frontend/.ai/frontend-ai-rules.md`
- `frontend/.ai/project-conventions.md`
