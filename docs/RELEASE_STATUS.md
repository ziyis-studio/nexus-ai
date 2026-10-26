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

- 72 backend tests passed; selected business modules 84.52% coverage.
- 27 RLS/grant/constraint scenarios passed on both WASM PostgreSQL and native PostgreSQL 18.4.
- 3 real PostgreSQL/PostgREST/API persistence/isolation integration scenarios passed.
- Complete browser workflow, Viewer restrictions, knowledge management and mobile/session/keyboard scenarios implemented; final rerun recorded with the release commit.
- Nuxt production build and frontend typecheck passed.
- SQL benchmark used 10,000 tickets and 10 concurrent native database clients; raw measured plans retained.
- Runtime npm dependency audit: zero findings. Development node-forge advisory remains documented in SECURITY.md.

## Pending external gates

- GitHub Actions final execution and Docker image builds: tracked on the implementation pull request.
- Actual local Supabase Auth/pgTAP/advisor pipeline: provided as a separate CI job; no hosted result is inferred from the portable auth harness.
- Hosted Supabase provisioning, real-account cloud sign-in and revocation, production WSS/origin configuration, a real OpenAI inference and deployed performance measurements require owner-selected infrastructure and secrets.
- Upstream development TLS dependency advisory requires continued review. The P0 production acceptance gate is not declared passed while this remains unresolved.

The portable preview is a functioning review environment with native PostgreSQL and PostgREST, synthetic identity, Fakeredis transport and deterministic model output. It is never a claim of real OpenAI inference or a hosted production deployment. The existing Planner Core Supabase project has not been modified.
