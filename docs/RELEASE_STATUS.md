# Release status

Implementation candidate for PRD P0. This document distinguishes source completion and local evidence from external staging acceptance.

## Implemented

- Nuxt dashboard: login, workspaces, ticket search/filter/pagination/create/edit/lifecycle, AI workspace/history/citations, review, knowledge create/edit/archive, run history, admin directory and audit trail.
- FastAPI typed REST and WebSocket services with consistent errors and OpenAPI contract.
- Supabase JWT/session validation, fresh membership/RBAC, explicit grants and RLS, composite tenant constraints, append-only audit and transactional commands.
- Redis Streams worker with bounded retries/deadline, persisted attempts, lease recovery/fencing, outbox reconciliation and idempotent completion.
- OpenAI Responses structured-output adapter with input/reference constraints and independent schema/citation validation.
- Docker application services, health checks, pinned locks, automated CI and operational documentation.

## Interface redesign

The app uses shadcn-vue / Reka Nova components throughout login, workspaces, the responsive shell, tickets, AI review, knowledge, history and settings. Device appearance, keyboard navigation, accessible dialogs and refreshed visual evidence are documented in [UI_DESIGN.md](UI_DESIGN.md).

## Local evidence

- 74 backend tests passed; selected business modules 85.19% coverage. The OpenAI SDK adapter was exercised against mocked structured-output and refusal responses.
- 28 RLS/grant/constraint scenarios passed on both WASM PostgreSQL and native PostgreSQL 18.4.
- 3 real PostgreSQL/PostgREST/API persistence/isolation integration scenarios passed.
- 9 browser journeys passed: core workflow/tenant isolation, Viewer restrictions, knowledge/audit, mobile/session/logout, interrupted-request replay, quick navigation/theme persistence, search/dialog focus, ticket editing/final rejection and automated WCAG A/AA checks on seven core light/dark surfaces.
- Nuxt production build and frontend typecheck passed.
- SQL benchmark used 10,000 tickets and 10 concurrent native database clients; raw measured plans retained.
- Full and production-only npm dependency audits: zero findings. The Nuxt TLS toolchain is pinned to patched node-forge 1.4.1.

## CI verification

All six jobs passed for application commit [`e3e7fef`](https://github.com/ziyis-studio/nexus-ai/actions/runs/40397925356): backend, web, native database, real Redis integration/browser tests, Docker builds, and real local Supabase. Supabase pgTAP reported 10 passing grant/RLS checks; security advisors passed the error-level gate; the real Auth-to-worker-to-review and logout/revoked-session scenario passed. Later documentation/benchmark/preview updates are rechecked on the PR before merge.

## Hosted database

The DEMO / Nexus Supabase database (`qgooyiokuclpijdwdpzt`) is provisioned with all versioned migrations, seven RLS-protected tables, nineteen policies and the two demo tenants. Hosted PostgreSQL rollback checks passed for isolation, permissions and the analysis/review lifecycle; anonymous HTTPS reads of all seven tables were denied. Security advisors report zero findings, with no performance warnings. [Connection details and verification limits](HOSTED_DATABASE.md).

## Remaining staging configuration

- Real-account cloud sign-in and revocation, application/Redis hosting, a dedicated worker login, production WSS/origin configuration, a real OpenAI inference and deployed performance measurements require hosting configuration and server-side secrets.
- The earlier TLS dependency advisory is addressed by the pinned patch. Production acceptance still requires the real-account/provider and hosting checks above.

The portable preview is a functioning review environment with native PostgreSQL and PostgREST, synthetic identity, Fakeredis transport and deterministic model output. It is never a claim of real OpenAI inference or a hosted production deployment. The existing Planner Core Supabase project has not been modified.
