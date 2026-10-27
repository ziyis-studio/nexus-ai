# Hosted NEXUS database

Provisioned on 2026-10-27 in the owner's selected **DEMO** organization, **Nexus** project. This records database provisioning separately from application deployment.

- [Supabase project dashboard](https://supabase.com/dashboard/project/qgooyiokuclpijdwdpzt)
- Project reference: `qgooyiokuclpijdwdpzt`
- Organization ID: `yynfjjaauwxqfldteuof`
- Region: `ap-south-1`; PostgreSQL 17.11
- Public API URL: `https://qgooyiokuclpijdwdpzt.supabase.co`
- Auth issuer: `https://qgooyiokuclpijdwdpzt.supabase.co/auth/v1`
- Published JWT signing algorithm checked through JWKS: `ES256`

## Applied schema

All four repository migrations are applied, in order:

1. `20261026200302_nexus_p0`
2. `20261026203950_utc_usage_window`
3. `20261027060639_hosted_database_indexes`
4. `20261027061216_hosted_function_grants`

The Supabase connector assigns deployment timestamps when applying SQL. The four newly created history rows were reconciled to the canonical repository versions, preserving their names and SQL statements. Future CLI migrations can compare against these repository versions without reapplying the baseline.

Seven business tables have RLS enabled: tenants, memberships, tickets, knowledge documents, analysis runs, AI results and audit logs. Nineteen policies enforce member roles and restricted background-worker access. Five actor foreign keys have covering indexes; three policies cache request identity per statement. Public command entrypoints explicitly revoke anonymous and service-role execution, including grants supplied by hosted defaults.

The two approved demo tenants, Acme Corporation and Nova Technologies, are seeded. Auth users, memberships and customer/business records are empty. No real login accounts or passwords were created.

## Verification

- `scripts/verify-hosted-db.sql` passed on the actual hosted database. It checks tenant isolation, viewer restrictions, forged metadata, membership revocation, idempotent analysis commands, worker permissions, document citation isolation, immutable terminal runs, final reviews and exactly-once review audit. All fixture identities and records were rolled back.
- This SQL test supplies request claims as an administrator to exercise PostgreSQL roles and the real Supabase `auth.uid()`. It does not prove JWT signature validation or real-account cloud sign-in.
- HTTPS Data API reads using the project's publishable key returned `401` for all seven business tables without a user token.
- Security advisor: zero findings. Performance advisor: zero warnings; remaining [unused-index information](https://supabase.com/docs/guides/database/database-linter?lint=0005_unused_index) is expected in a new database without application traffic. Keep the indexes until representative workload evidence supports removal.
- The repository's 28 SQL checks pass with hosted-style default function grants simulated. CI also runs the rollback smoke on actual local Supabase.

## Application connection

Use the public URL and issuer above, the project's **publishable** key, and `JWT_ALGORITHMS=["ES256"]`. Set `VERIFY_SESSION=true`. The web build uses the same public URL/key; database passwords, service-role keys and provider credentials belong only in server configuration.

An ignored `.env.hosted` profile in the working checkout contains the verified public connection values. Its database URL, Redis URL, API base URL, allowed frontend origins and server credentials still need hosting-specific values before it can run the deployed application. The checked-in `.env.example` remains the local development template.

Provision app users through the existing Auth Admin API seed workflow or an owner-approved real-user onboarding process; never insert durable Auth accounts directly through SQL. Give the deployed worker a dedicated login that is a member of `nexus_worker`, using a direct or session-pooler connection. No worker login/password has been generated as part of schema provisioning.

Frontend/API/worker hosting, real-user sign-in and revocation, production WebSocket origins, Redis, real OpenAI inference and deployed performance acceptance remain separate deployment steps. See [deployment guidance](DEPLOYMENT.md).
