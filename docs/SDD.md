# Software design document

## Scope

The supplied PRD is preserved in [PRD.md](PRD.md). This implementation covers its P0 workflow. Invitations, semantic embeddings, billing, outbound messaging, multiple live providers and advanced analytics remain P1/P2. English UI accepts Chinese and English ticket content. All stored timestamps are UTC.

## Modules and boundaries

- `apps/web`: Nuxt 4, Vue, TypeScript, Tailwind CSS, Supabase Auth client, native WebSocket.
- `services/api/app/auth`: pinned algorithm allowlist, signature/issuer/audience/expiry/UUID checks, live session verification.
- `repositories`: request-local HTTPX clients to Supabase Data API, error translation and stable pagination.
- `services/workspace`: trusted membership and role authorization.
- `routers`: typed REST contracts and authenticated WebSocket subscriptions.
- `services/worker`: Redis consumer group, PostgreSQL leases and fenced commits, provider adapter and grounding validation.

## User operations and transactions

FastAPI verifies the token before loading current membership. Resource queries always include tenant ID. A foreign resource inside an authorized workspace returns 404; a workspace without membership returns 403. No permission depends on user-editable metadata.

Each CRUD insert/update is one Data API database transaction. Ticket/document auditing is an AFTER trigger in that same transaction, so audit failures roll back the business write. Identity fields and lifecycle transitions have database checks in addition to API schemas.

Two narrow database commands are transactional: analysis creation and review. Public RPC wrappers use SECURITY INVOKER and call private, reviewed SECURITY DEFINER functions. The private functions authenticate with `auth.uid()`, check membership from tables, use fully qualified names and empty `search_path`, and accept no SQL. Their purpose and grants are detailed in SECURITY.md.

Analysis creation takes a transaction advisory lock on the tenant. It checks idempotency before capacity limits, snapshots the ticket, and writes both the queued run and audit event. The request fingerprint contains ticket ID and model ID, which are the entire analyze request payload. A ticket edited after submission does not change that run's snapshot. Reusing a key with a different ticket/model conflicts; replaying an identical request returns the original run.

P0 workspace limits are centralized in the database: at most 10 unfinished runs, 20 new runs per minute, and 200 per UTC day. Change these reviewed SQL limits in a migration. Worker concurrency, model, output tokens, timeouts and attempt limits are environment configuration. The worker only executes the configured model; direct RPC callers cannot select a more expensive model.

Review locks the result row. The first decision records actor/time and is final. Identical repeats return the stored decision without writing another event. An opposite decision returns 409. A fresh analysis creates a fresh result. Approval never sends a customer message.

## Queue, leases and recovery

1. Commit `analysis_runs(status=queued)` before enqueue. This durable row is the outbox. Redis failure does not erase accepted work.
2. Redis Streams uses `nexus:jobs` / consumer group `nexus-workers`. Workers use XREADGROUP and XAUTOCLAIM.
3. An atomic PostgreSQL UPDATE claims a queued run or an expired processing lease, assigning a random lease token. Healthy competing claims affect zero rows.
4. The default lease is 240 seconds, longer than the 180-second overall job deadline. A lease is not renewed; the deadline makes it unnecessary. The original `started_at` remains across crashes.
5. Retry count is persisted before each provider call. Three attempts include the first attempt. Network errors, 429s, timeouts and provider 5xx use exponential backoff with jitter. Validation, malformed output, authorization and permanent provider errors are not blindly retried.
6. Completion locks the run and checks its tenant, status and lease token. Result insertion, terminal status and the safe execution audit commit together. A superseded worker cannot write through an old token.
7. Acknowledge and remove the stream message only after durable terminal state. Failed commits leave the message pending.
8. Every ten seconds the reconciler scans stale queued rows and expired leases. A Redis NX key bounds re-enqueue frequency. A lost Redis dataset is repaired from PostgreSQL. Duplicate delivery is expected and harmless.

Use `scripts/recovery-drill.py` and the persistence integration test to reproduce an expired lease and demonstrate fencing. Terminal runs are immutable. Manual retry always creates a new run.

## Worker connections

Psycopg's async pool opens lazily with 1–`worker_concurrency + 2` connections. Each connection executes `SET ROLE nexus_worker` before returning to the pool. The login must be a member of that restricted NOLOGIN role. Use a direct/session-pooler connection; transaction pooling cannot preserve this session role safely. Every SQL query binds tenant and resource IDs. The role has no membership writes, ticket writes, review updates or business DELETE privileges.

For production, create a dedicated login through the hosting provider and grant it `nexus_worker`; keep its password outside Git. The local example uses the development PostgreSQL login and immediately drops privileges. API processes have no reason to use this connection string.

## Knowledge and model behavior

P0 retrieves at most four active tenant documents with PostgreSQL `simple` full-text search and a bounded Unicode substring fallback. Each excerpt is at most 2,400 characters. This is lexical retrieval, not semantic RAG; Chinese matching is limited without language-specific segmentation.

OpenAI Responses structured outputs are parsed into a Pydantic schema and independently checked for valid enums, lengths, booleans and references. Only retrieved IDs are accepted. Stored suggestions always require human review. Prompt v1 treats both customer text and documents as untrusted data, forbids invented business policies, and asks for clarification when references are insufficient. Text is rendered through Vue interpolation, never raw HTML.

The explicit `fixture` provider exists for tests and development only; production configuration rejects it. It is not a substitute for a real LLM validation run.

## Live state and frontend isolation

The WebSocket authenticates its first message within five seconds, validates allowed Origin, membership and run ownership, then reads persisted state. RLS is reevaluated on each poll; JWT and live session checks repeat at most every 15 seconds and before progress delivery. Redis progress is a hint. Polling at 750 ms reconstructs missed terminal state.

The client retries WebSocket connections with capped exponential backoff (six attempts) while polling REST every 2.5 seconds. Terminal status comes from REST; duplicate/out-of-order progress cannot roll it backward. Navigation tears down the watcher and mounts a fresh tenant-scoped page. Ticket search aborts superseded requests. Data caches are page-local; memberships are refreshed on navigation.

## Observability

JSON logs carry UTC timestamp, severity, service, event and request/run/tenant IDs when applicable. API logs route templates rather than query strings and record status/latency. Worker logs duration, persisted attempts and safe error codes. Queue samples expose stream depth; acknowledged messages are removed so depth reflects outstanding transport work. Credentials, prompts and customer message bodies are not logged. Access logs are disabled in the supplied runtime commands. Aggregate event logs for request/error counts, job success/failure counts, duration and retries. A full monitoring stack is P1.

## Engineering tradeoffs

The durable queued row plus reconciliation avoids an additional outbox table. Redis Pub/Sub accelerates progress but adds no durability contract. Private atomic commands are deliberately small because Data API calls cannot share a client-side transaction. JSON reference IDs are validated at insertion rather than introducing a join table in P0. No index speedup is claimed without measurements; the warm 10,000-row benchmark is described in PERFORMANCE.md.
