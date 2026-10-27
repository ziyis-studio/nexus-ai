# Release status

Implementation candidate for PRD P0. This document distinguishes source completion and local evidence from external staging acceptance.

## Implemented

- Nuxt dashboard: login, workspaces, ticket search/filter/pagination/create/edit/lifecycle, AI workspace/history/citations, review, knowledge create/edit/archive, run history, admin directory and audit trail.
- FastAPI typed REST and WebSocket services with consistent errors and OpenAPI contract.
- Supabase JWT/session validation, fresh membership/RBAC, explicit grants and RLS, composite tenant constraints, append-only audit and transactional commands.
- Redis Streams worker with bounded retries/deadline, persisted attempts, lease recovery/fencing, outbox reconciliation and idempotent completion.
- OpenAI Responses structured-output adapter with input/reference constraints and independent schema/citation validation.
- Docker application services, health checks, pinned locks, automated CI and operational documentation.

## Local evidence

- 74 backend tests passed; selected business modules 85.19% coverage. The OpenAI SDK adapter was exercised against mocked structured-output and refusal responses.
- 28 RLS/grant/constraint scenarios passed on both WASM PostgreSQL and native PostgreSQL 18.4.
- 3 real PostgreSQL/PostgREST/API persistence/isolation integration scenarios passed.
- 5 browser journeys passed: full workflow/tenant switch, Viewer restrictions, knowledge management/audit, mobile/session/keyboard/logout, and replay after a network interruption following analysis acceptance.
- Nuxt production build and frontend typecheck passed.
- SQL benchmark used 10,000 tickets and 10 concurrent native database clients; raw measured plans retained.
- Runtime npm dependency audit: zero findings. Development node-forge advisory remains documented in SECURITY.md.

## CI verification

All six jobs passed for application commit [`e3e7fef`](https://github.com/ziyis-studio/nexus-ai/actions/runs/40397925356): backend, web, native database, real Redis integration/browser tests, Docker builds, and real local Supabase. Supabase pgTAP reported 10 passing grant/RLS checks; security advisors passed the error-level gate; the real Auth-to-worker-to-review and logout/revoked-session scenario passed. Later documentation/benchmark/preview updates are rechecked on the PR before merge.

## Hosted database

The DEMO / Nexus Supabase database (`qgooyiokuclpijdwdpzt`) is provisioned with all versioned migrations, seven RLS-protected tables, nineteen policies and the two demo tenants. Hosted PostgreSQL rollback checks passed for isolation, permissions and the analysis/review lifecycle; anonymous HTTPS reads of all seven tables were denied. Security advisors report zero findings, with no performance warnings. [Connection details and verification limits](HOSTED_DATABASE.md).

## Remaining staging configuration

- Real-account cloud sign-in and revocation, application/Redis hosting, a dedicated worker login, production WSS/origin configuration, a real OpenAI inference and deployed performance measurements require hosting configuration and server-side secrets.
- Upstream development TLS dependency advisory requires continued review. The P0 production acceptance gate is not declared passed while this remains unresolved.

The portable preview is a functioning review environment with native PostgreSQL and PostgREST, synthetic identity, Fakeredis transport and deterministic model output. It is never a claim of real OpenAI inference or a hosted production deployment. The existing Planner Core Supabase project has not been modified.
