# Verification plan

## Fast checks

```sh
uv sync --frozen
npm ci
uv run ruff format --check services tests scripts
uv run ruff check services tests scripts
uv run mypy --explicit-package-bases services/api/app services/worker
uv run pytest --cov=app.services --cov=app.schemas --cov=app.repositories --cov=services.worker.ai --cov=services.worker.main --cov-fail-under=80
PYTHONPATH=services/api:. uv run python scripts/contract.py
node scripts/test-database.mjs
npm run format:check
npm run typecheck
npm run build
npm audit --omit=dev --audit-level=high
```

On PowerShell set `$env:PYTHONPATH='services/api;.'` before the contract command. Python packages are locked in uv.lock; npm packages in package-lock.json. PGlite runs real PostgreSQL SQL/RLS compiled to WASM, but it does not stand in for a concurrent production database.

## Native integration and browser checks

Start the portable sandbox or an equivalent configured test environment. Then:

```sh
node scripts/test-database.mjs --native
NEXUS_INTEGRATION=1 uv run pytest tests/integration -q
npx playwright install chromium
npm run test:e2e
uv run python scripts/benchmark.py
```

The native security script creates and drops its own temporary database, so its login needs CREATEDB on a disposable PostgreSQL cluster. It exercises actual PostgreSQL grants, RLS, immutable identities, tenant-consistent foreign keys, idempotency, review/audit behavior and terminal-state checks. The worker persistence scenario verifies competing claims, expired-lease takeover, old-token rejection and exactly one result. The HTTP integration scenarios exercise the real FastAPI/PostgREST/RLS boundary.

Browser journeys cover admin login, tenant selection, create ticket, async analysis, knowledge citations, approve, refresh/restore, switch organizations, Viewer restrictions, knowledge creation/archive, audit visibility, mobile overflow, native dialog Escape and logout. Generated screenshots and the recorded walkthrough use synthetic records. Fakeredis is used in the portable Windows preview; the CI integration job uses a real Redis container.

## Actual Supabase verification

The separate CI `supabase` job starts Supabase's real local Auth, gateway, Data API and database, applies the migration, checks security advisors and pgTAP, provisions accounts using Supabase Admin APIs, then runs sign-in → ticket → worker result → review → logout/session-revocation verification. The model is still a deterministic fixture. The portable auth shim is never accepted as evidence for this job.

`supabase/tests/rls.test.sql` checks RLS/grants/helper exposure with pgTAP. The larger native SQL suite independently tests row behavior and constraints. Hosted Supabase and actual OpenAI calls remain additional staging checks requiring configured owner credentials.

## Security coverage

Tests include missing/expired/incorrect-signature/issuer/audience/algorithm JWTs, malformed UUID identity, revoked sessions, unauthorized tenant and foreign ticket/result/knowledge access, Viewer mutations, body tenant/actor spoofing, WebSocket Origin/auth/cross-tenant denial, SQL-like input as text, duplicate submission, model-output enums/lengths/types, invented sources, transient retry, no retry for invalid output, deadline failure and unacknowledged failed commits.

## Evidence and limits

See RELEASE_STATUS.md for current counts and remote CI state. SQL performance evidence is under `docs/evidence/sql-benchmark.json`; raw plans include buffers and actual timings. The coverage gate targets business schemas/services/repository/provider/worker execution, not generated UI or infrastructure adapters. Coverage is supporting evidence; the native and browser scenarios are the primary end-to-end evidence.

Full development-dependency audit findings are documented in SECURITY.md, including the upstream node-forge issue. Production dependency audit and disabled development TLS features do not make that upstream advisory disappear.
