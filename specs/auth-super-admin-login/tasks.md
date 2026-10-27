---
slug: auth-super-admin-login
title: Local super-admin JWT authentication
author: Yasin Serhat Peker
area: backend
status: active
created: 2026-10-27 15:35
updated: 2026-10-27 16:05
---

# Tasks — Local super-admin JWT authentication

## Phase 0 — Probe and gates

- [x] Read applicable backend/frontend rules and the existing demo-token implementation.
- [x] Record the JWT, bcrypt, bootstrap and browser-token decisions.
- [x] Confirm multiple-super-admin policy, database-backed refresh behaviour and all pending gates.

## Phase 1 — Implement

- [x] Add maintained JWT/bcrypt dependencies, CSRF/origin protections, security headers and secure local configuration.
- [x] Document and test local multiple-super-admin creation with Django's standard command.
- [x] Add bounded email/password login, CSRF and JWT refresh/logout endpoints with contract tests.
- [x] Replace shared demo-token authentication on protected API routes with JWT authentication.
- [x] Replace dashboard token entry with Turkish email/password login, access-token state and refresh restoration.
- [x] Add dashboard logout, CSRF handling and protected request handling.
- [x] Add bounded throttling, security regression tests and CI checks.
- [x] Update local environment examples, documentation, Docker startup and CI.

## Phase 2 — Verification record

| Criterion | Tag | Evidence |
|---|---|---|
| Super-admin bootstrap and JWT API contract | `auto:test` / `auto:compose-test` | `docker compose --env-file .env.example up --detach --build --wait`; 17 Django tests passed on 2026-10-27. |
| Bcrypt password storage | `auto:test` | `test_active_superuser_can_log_in_with_bcrypt_password_and_refresh_cookie` passed on 2026-10-27. |
| Login/logout UI and token memory boundary | `auto:frontend-test` / `manual:ui` | `npm run build` passed; local login screen inspected at `http://localhost:5174` on 2026-10-27. |

- [x] Record every automatic command result.
- [ ] Confirm the commit trailer uses `Spec: auth-super-admin-login` after commit approval.
