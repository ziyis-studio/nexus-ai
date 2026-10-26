# Security design and review

## Identity and authorization

Supabase issues browser sessions. FastAPI verifies a pinned signing-algorithm allowlist, cryptographic signature, issuer, audience, expiry, issued-at and UUID subject. Asymmetric keys are fetched from the configured Supabase JWKS endpoint and cached for five minutes; network refresh remains bounded. Legacy local HS256 is available only when explicitly enabled with a server secret. Tokens never appear in URLs or logs.

The API also validates Supabase `/user` and the signed token's `session_id` against `auth.sessions`, so revoked sessions lose API access before JWT expiry. Membership is read from active database records for every request. Session and membership are rechecked during live subscriptions. Auth infrastructure failure returns 503 rather than accepting an unchecked identity.

Admins and agents can manage tickets, run analysis and review. Only admins write knowledge or read membership/audit history. Viewers can only read. Roles are never sourced from user metadata.

## Database boundary

All seven exposed tables have RLS. SQL grants explicitly expose the required columns/operations, including separate SELECT and UPDATE policies. No user DELETE policy or grant exists. Tenant identity, primary keys, creator and creation time cannot be reassigned. Composite foreign keys and unique constraints enforce tenant-consistent relationships and one result per run.

Privileged function review:

| Private function  | Why elevated access is necessary                                                   | Guard                                                                              |
| ----------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `has_role`        | Read memberships without recursive RLS                                             | Uses only current `auth.uid()`, checks active membership, returns boolean          |
| `create_analysis` | Atomic idempotency, quotas, snapshot and audit without allowing direct run inserts | Non-null identity, role check, scoped ticket, tenant advisory lock, bounded inputs |
| `review_analysis` | Final review under a row lock without giving clients arbitrary result UPDATE       | Identity/role check, scoped result, decision allowlist, immutable first review     |
| `session_active`  | Read the private auth session table                                                | Current identity plus JWT session ID only; returns boolean                         |
| `audit_change`    | Append audit row from otherwise restricted writes                                  | Trigger only; EXECUTE revoked from authenticated/PUBLIC; no freeform audit payload |

Every SECURITY DEFINER function lives in unexposed `nexus_private`, has an empty `search_path`, fully qualifies table references and revokes default PUBLIC execution. Only needed boolean/command helpers are executable by authenticated callers. Public RPC wrappers are SECURITY INVOKER. No helper accepts SQL, a caller-selected actor identity, or a database role.

`nexus_worker` is NOLOGIN with explicit RLS policies and grants, rather than BYPASSRLS. It can read required input, claim/update runs, insert a result and append a safe audit. It cannot edit tickets, membership, knowledge or reviews. Python still checks tenant/resource associations, initiating membership and fencing tokens. A queue message containing a foreign tenant/run combination cannot claim the run. Worker execution also rejects a model differing from the configured provider model.

## AI and rendering

Schema validation is mandatory after generation. Citation IDs must be drawn from retrieved active tenant documents and pass a database validation trigger. The model cannot execute SQL or tools. Customer messages and knowledge are untrusted text. Every suggestion stays pending until an authorized review; approval never transmits customer communications. Vue escapes all user/model text. Human review remains necessary for factual correctness and prompt-injection attempts; a prompt is not a complete hallucination guarantee.

## Deployment

Production configuration requires HTTPS origins and Supabase URL, live-session validation and a real provider key. Terminate HTTPS/WSS at your reverse proxy, expose no database/Redis ports publicly, set exact origins, and use synthetic portfolio records. The API should be reachable only through its reverse proxy in production. Restrict infrastructure access and rotate all server credentials outside source control.

The public project key is intentionally public. No service-role key belongs in `NUXT_PUBLIC_*`. `.env`, `.local`, auth tokens and test traces are ignored. The provisioning script never prints credentials. The portable QA auth adapter is not packaged in service images and must never be deployed.

## Dependency review

The lockfiles pin resolved versions. Production `npm audit --omit=dev --audit-level=high` reports zero findings in the verified dependency set. Nuxt/build tooling currently includes a transitive `node-forge` advisory, GHSA-86w9-cpqp-85rv, propagated through local TLS certificate tooling. The registry has no patched node-forge release at the checked version; this is not silently waived as fixed. Nuxt is pinned to 4.6.2 with DevTools disabled, local preview binds to loopback, production serves the generated output, and authentication uses PyJWT/cryptography rather than node-forge. Recheck full development dependencies before exposing a development server or changing TLS handling. See the release status for this unresolved upstream advisory.

The P0 production acceptance gate remains conditional on reviewing this upstream development dependency advisory and completing a real Supabase/LLM staging verification. Passing synthetic tests does not certify a production deployment.
