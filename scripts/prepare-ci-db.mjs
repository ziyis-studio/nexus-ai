// Only run against an empty, disposable PostgreSQL database.
import pg from 'pg'
import { shim, migrate, seed, ids } from './test-database.mjs'

if (!process.env.DATABASE_TEST_URL) throw new Error('Set DATABASE_TEST_URL for a disposable database.')
const client = new pg.Client({ connectionString: process.env.DATABASE_TEST_URL })
await client.connect()
try {
  if ((await client.query("select 1 from pg_namespace where nspname='nexus_private'")).rowCount)
    throw new Error('Refusing to prepare an existing NEXUS database.')
  const adapter = { exec: (sql) => client.query(sql), query: (sql, params) => client.query(sql, params) }
  await adapter.exec(shim)
  await migrate(adapter)
  await seed(adapter)
  await adapter.exec(`create or replace function auth.uid() returns uuid language sql stable as $$ select coalesce(nullif(current_setting('request.jwt.claim.sub',true),''),current_setting('request.jwt.claims',true)::jsonb->>'sub')::uuid $$;
    create role authenticator login password 'nexus-local-only' noinherit;
    grant authenticated,anon to authenticator;
    grant usage on schema public to anon;`)
  for (let n = 0; n < 8; n++)
    await client.query(
      'insert into public.tickets(tenant_id,subject,description,created_by) values($1,$2,$3,$4)',
      [
        ids.a,
        `Synthetic support conversation ${n + 1}`,
        'A synthetic customer request for reproducible integration testing.',
        ids.admin,
      ],
    )
  console.log('Prepared disposable PostgreSQL identity shim, schema and synthetic records.')
} finally {
  await client.end()
}
