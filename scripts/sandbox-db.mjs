// Portable QA harness. Real native PostgreSQL + schema shim, NOT Supabase Auth.
import EmbeddedPostgres from 'embedded-postgres'
import { mkdir, readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { shim, migrate, seed, ids } from './test-database.mjs'

await mkdir('.local', { recursive: true })
const pg = new EmbeddedPostgres({
  databaseDir: resolve('.local/pg'),
  user: 'postgres',
  password: 'nexus-local-only',
  port: 55432,
  persistent: true,
  initdbFlags: ['--encoding=UTF8', '--locale=C'],
  postgresFlags: ['-c', 'listen_addresses=127.0.0.1'],
  onLog: () => {},
  onError: (message) => console.error(message),
})
try {
  await readFile('.local/pg/PG_VERSION')
} catch {
  await pg.initialise()
}
await pg.start()
const db = pg.getPgClient()
await db.connect()
const query = (sql, params) => db.query(sql, params)
const adapter = { exec: (sql) => db.query(sql), query }
if (!(await query("select 1 from pg_namespace where nspname='nexus_private'")).rowCount) {
  await adapter.exec(shim)
  await migrate(adapter)
  await seed(adapter)
  // Auth compatibility functions needed by PostgREST; user ID stays in signed claims.
  await adapter.exec(`create or replace function auth.uid() returns uuid language sql stable as $$ select coalesce(nullif(current_setting('request.jwt.claim.sub',true),''),current_setting('request.jwt.claims',true)::jsonb->>'sub')::uuid $$;
    create role authenticator login password 'nexus-local-only' noinherit;
    grant authenticated,anon to authenticator;
    grant usage on schema public to anon;
    notify pgrst,'reload schema';`)
  const subjects = [
    'Invoice charged twice for October',
    'Cannot reset account password',
    'Application crashes on export',
    'Question about the enterprise plan',
    'Urgent: production integration is blocked',
    'Change the delivery address',
    'Thanks for the fast resolution',
    '订单延迟，需要查询物流进度',
  ]
  for (let i = 0; i < subjects.length; i++)
    await query(
      `insert into public.tickets(tenant_id,subject,description,customer_name,created_by) values($1,$2,$3,$4,$5)`,
      [
        ids.a,
        subjects[i],
        `Customer support request: ${subjects[i]}. Please review the request and confirm the appropriate next steps.`,
        [
          'Sam Rivera',
          'Jamie Chen',
          'Taylor Brooks',
          'Casey Williams',
          'Jordan Lee',
          'Riley Park',
          'Morgan Reed',
          '林女士',
        ][i],
        ids.admin,
      ],
    )
}
console.log('Native PostgreSQL QA database ready on 127.0.0.1:55432')
await db.end()
const shutdown = async () => {
  await pg.stop()
  process.exit(0)
}
process.on('SIGINT', shutdown)
process.on('SIGTERM', shutdown)
setInterval(() => {}, 60000)
