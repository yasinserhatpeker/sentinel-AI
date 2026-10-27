---
slug: auth-super-admin-login
title: Local super-admin JWT authentication
author: Yasin Serhat Peker
area: backend
status: active
verification: full
created: 2026-10-27 15:35
updated: 2026-10-27 16:05
branches: core-development
---

# Local super-admin JWT authentication

## Problem

The local dashboard currently asks for a shared demo token. This is not a usable login
experience and gives no named administrator identity for protected local API requests.

## Scope

**In:** one or more developer-created local super-admins; username-or-email/password login; Django's built-in
`User` model; bcrypt-backed password hashing through `BCryptSHA256PasswordHasher`; JWT access and
refresh tokens from `djangorestframework-simplejwt`; database-backed refresh-token rotation and
revocation; OWASP-aligned browser/session protections; JWT authentication for protected API
routes; a Turkish Vue login screen with English technical terms; persistent local session
restoration; logout; and migration-free local Docker/CI coverage.

**Out:** sign-up, password reset, multiple roles, user management UI, social login, email sending,
production identity provider integration, and changes to the telemetry data schema.

**Existing behaviour preserved:** health remains public; the local dashboard, explicit telemetry
scope controls and local Compose-only topology remain; order and telemetry APIs remain protected,
but switch from the shared demo-token scheme to `Bearer` JWT authentication.

## Acceptance criteria

- [ ] Django's documented local `createsuperuser` workflow creates one or more super-admins
      without writing credentials to source, environment configuration or logs. → `manual:api`
- [ ] A valid email/password login receives a JWT access token and sets a protected refresh cookie;
      malformed or invalid credentials return a stable error without leaking account existence. → `auto:test`
- [ ] Protected order, telemetry write and telemetry read routes accept valid `Bearer` access
      tokens and reject missing, invalid or expired tokens. → `auto:test`
- [ ] Passwords are stored with Django's bcrypt SHA-256 hasher, never logged or returned. → `auto:test`
- [ ] The Vue login screen is Turkish, keeps technical terms in English, uses the established
      corporate green design, restores the local session after refresh, and never exposes the
      refresh token to JavaScript. → `manual:ui`
- [ ] Login, refresh and logout enforce CSRF/origin protections; refresh uses an `HttpOnly`,
      `SameSite=Lax` cookie with secure production attributes. → `auto:test`
- [ ] CSP, clickjacking, MIME-sniffing, referrer, permission-policy and cache-control headers are
      present for applicable frontend/API responses. → `auto:test`
- [ ] Bounded login throttling and generic authentication failures resist basic credential
      stuffing and account enumeration. → `auto:test`
- [ ] Logout revokes the active refresh token, clears its cookie and returns the user to login. → `auto:frontend-test`

## Affected areas

| Area | Planned change |
|---|---|
| `backend/config/` | JWT authentication, bcrypt hasher and security configuration. |
| `backend/demo/` | Login/refresh API, authentication tests and JWT-protected routes. |
| `frontend/` | Login view, in-memory auth state, Bearer API service and logout action. |
| `.env.example` | JWT signing-key configuration without account credentials. |
| `docs/`, `README.md` | Local credential setup and sign-in walkthrough. |
| `specs/` | Auth contract, decisions and verification evidence. |

## Open questions

None. Resolved 2026-10-27: multiple independently created local Django super-admins are allowed;
only active superusers may log in; the short-lived access token stays in runtime memory; the
rotating database-backed refresh token uses an `HttpOnly`, `SameSite=Lax` cookie.
