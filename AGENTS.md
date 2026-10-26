# Repository guidance

Read README.md, docs/PRD.md, docs/SDD.md, docs/SECURITY.md and docs/RELEASE_STATUS.md before changing behavior.

P0 is the scope. Keep user business queries user-scoped through Supabase Data API. Never use service-role credentials to bypass user RLS. Authorization comes from current membership, never user metadata. Preserve tenant-bound composite keys, idempotency, final reviews, terminal runs and fenced worker commits. No automatic customer-message delivery.

Use Node 24.22.1 and Python 3.12.14. Dependency resolutions belong in package-lock.json and uv.lock. Create migrations with the pinned Supabase CLI. No secrets or synthetic auth adapters in deployment images. Keep the portable QA harness explicitly separate from Supabase verification.

Required checks after functional changes:

```
uv run ruff format --check services tests scripts
uv run ruff check services tests scripts
uv run mypy --explicit-package-bases services/api/app services/worker
uv run pytest --cov=app.services --cov=app.schemas --cov=app.repositories --cov=services.worker.ai --cov=services.worker.main --cov-fail-under=80
PYTHONPATH=services/api:. uv run python scripts/contract.py
node scripts/test-database.mjs
node scripts/test-database.mjs --native
npm run typecheck
npm run build
npm run test:e2e
```

Native database and browser/integration checks require a running configured test environment; report what ran and what remains unverified. Never label fixture-provider or synthetic-auth tests as real Supabase/OpenAI production evidence.
