# Development, deployment and recovery

## Requirements

Node 24.22.1, Python 3.12.14, uv and Git. The supported full environment also requires Docker/Compose and a local or hosted Supabase project. Install pinned dependencies with `npm ci` and `uv sync --frozen`. On Windows, select Node 24 before running npm; a different npm.cmd can otherwise launch an older installed Node. The project has been built with Node 24.22.1.

## Portable preview without Docker

```sh
npm ci
uv sync --frozen
npm run sandbox
```

Visit `http://127.0.0.1:3000`. Synthetic accounts: `admin@nexus.test`, `agent@nexus.test`, `viewer@nexus.test`; password `Nexus-demo-2026!`. Admin can switch between Acme and Nova. Agent/viewer belong only to Acme. The launcher runs native PostgreSQL and official PostgREST, with an explicit synthetic auth adapter, Fakeredis test transport and deterministic fixture LLM. It never silently uses these in production. Keep this loopback-only harness private. It persists its isolated database under ignored `.local/pg`; do not use real customer information. Stop it with Ctrl+C.

The launcher downloads a pinned official PostgREST release when absent. Platform PostgreSQL binaries come from the locked embedded-postgres development package. This preview needs no real account passwords or LLM credentials.

## Actual local Supabase

```sh
npm ci
uv sync --frozen
npx supabase start
```

Migrations and `supabase/seed.sql` initialize the local database. For a clean disposable reset use `npx supabase db reset` after confirming you do not need existing local data. Never reset a hosted project as a troubleshooting shortcut.

Copy `.env.example` to `.env`, fill the project public key, server JWT settings, database URL and your server-side OpenAI key. Local CLI versions may issue HS256 tokens; explicitly allow HS256 and use the CLI-provided local JWT secret. Hosted projects should use their configured asymmetric algorithm and JWKS. Keep issuer equal to the public Supabase auth URL even when using internal container addresses.

Provision demo identities through the Auth Admin API:

```sh
uv run python scripts/seed.py
```

This requires `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL` and a unique `DEMO_PASSWORD` of at least 12 characters. It creates synthetic accounts without printing credentials and preserves existing users. It does not fabricate Supabase auth rows or change existing user passwords.

For application containers, set the internal Supabase URLs in `.env` to `http://host.docker.internal:54321/auth/v1` and `http://host.docker.internal:54321/rest/v1`; set `DATABASE_URL` host to `host.docker.internal:54322`. Browser `NUXT_PUBLIC_*` values must remain reachable from the user's browser (normally `127.0.0.1`). Then:

```sh
docker compose up --build -d
docker compose logs -f api worker
```

Redis, API, worker heartbeat and web health checks are configured. Redis persists AOF data in `redis-data`; Supabase owns database persistence separately. `docker compose down` stops application services and preserves the volume. `npx supabase stop` stops local Supabase. Do not add `--volumes` unless intentionally discarding queue storage.

For the real local Supabase test path without putting credentials into terminal output, see the `supabase` CI job: save `supabase status -o json` to ignored `.local/supabase-status.json`, then run `uv run python scripts/run-supabase-services.py --web`. This uses real local Supabase identity with the explicit fixture LLM.

## Hosted staging

The DEMO / Nexus hosted database has been provisioned; see [its current schema, connection details and verification](HOSTED_DATABASE.md). This does not imply that the application services are deployed.

1. Choose a dedicated Supabase project and apply the versioned migrations with the pinned CLI. The existing Planner Core project is unrelated and must not be modified.
2. Configure the public Supabase URL/key and exact HTTPS frontend origins. Set `ENVIRONMENT=production`, keep `VERIFY_SESSION=true`, configure the actual JWT algorithm, and set the server OpenAI key/model.
3. Create a dedicated database login with membership in `nexus_worker`. Use a direct database or session-pooler connection; transaction pooling does not preserve `SET ROLE`.
4. Run Redis privately with persistence, and deploy API/worker separately. Build the web image with browser-reachable public values. Never put provider, service-role or database secrets in web build arguments.
5. Terminate HTTPS/WSS at your platform proxy. Allow only that proxy to reach API ports. Supabase, Redis and database credentials belong in the hosting secret store.
6. Run real-account sign-in, revoked-session, RLS, WebSocket reconnect, provider failure, successful LLM output and response-review smoke tests before accepting staging.

The repository provides Docker images and CI build verification. It does not provision a paid hosting account, Redis hosting or a public production deployment. A real OpenAI call requires the owner's server-side API key and remains a distinct verification step.

## Operational recovery

If Redis is unavailable, accepted runs remain queued in PostgreSQL. Restore Redis and restart a worker; reconciliation republishes missing work. If a worker dies mid-call, allow its lease to expire. A replacement claims it with a different token; the old token cannot commit. The original job deadline bounds work across restarts. Jobs older than that deadline fail with a safe terminal code rather than staying hidden indefinitely.

For a terminal failure, inspect the run's safe error code, fix the dependency or input, then launch a new analysis. Do not mutate a failed/succeeded run back to queued or delete its history. `uv run python scripts/recovery-drill.py` demonstrates fencing in the configured synthetic test database.

Back up PostgreSQL using your provider's supported backup/export facility. Redis is recoverable transport and is not the only record of accepted work. Restore schema/data together and reconcile unfinished rows before accepting new AI work. Rotate provider/service/database credentials if exposure is suspected; revoke sessions and memberships as appropriate.
