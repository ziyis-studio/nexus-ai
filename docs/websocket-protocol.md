# WebSocket protocol v1

Connect to `/ws/v1/tenants/{tenant_id}/runs/{run_id}` using WSS in deployed environments. The browser Origin must match the exact configured allowlist. Within five seconds send:

```json
{ "type": "authenticate", "token": "<Supabase access token>" }
```

Do not put the token in a URL. No tenant data is sent before signature/session/membership/run checks. Close code 4401 means missing, expired or invalid authentication; 4403 means unauthorized origin, tenant or resource. Terminal jobs send the persisted terminal event then close normally (1000).

```json
{
  "event_id": "ac5b011e-944b-445c-a5be-20a66227ec15",
  "tenant_id": "10000000-0000-4000-8000-000000000001",
  "run_id": "219d5722-cfbd-4a94-9d70-0bc98b3f4981",
  "type": "run.progress",
  "status": "processing",
  "timestamp": "2026-10-27T00:00:00+00:00",
  "payload": { "stage": "retrieving" }
}
```

Types: `run.queued`, `run.started`, `run.progress`, `run.completed`, `run.failed`. Status changes come from PostgreSQL, not Pub/Sub. Progress stages are `retrieving`, `analyzing`, `retrying`; these have no ordering/durability guarantee. Status payloads include safe attempt/error-code metadata only.

Events are best effort and can be missed, duplicated, delayed or reordered. They do not contain ticket text or suggested replies. Clients must retrieve the current run/result from authenticated REST. NEXUS uses capped exponential reconnect delays, reauthenticates every connection, polls REST as a fallback and disposes subscriptions on tenant navigation. Session/membership checks recur on the server during an open connection. Do not use Pub/Sub or WebSocket event history as the source of truth.
