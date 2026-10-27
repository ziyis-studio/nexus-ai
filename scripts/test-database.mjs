import { PGlite } from '@electric-sql/pglite'
import { readFile, readdir } from 'node:fs/promises'
import assert from 'node:assert/strict'
import { performance } from 'node:perf_hooks'

export const shim = `
do $$ begin create role anon nologin; exception when duplicate_object then null; end $$;
do $$ begin create role authenticated nologin; exception when duplicate_object then null; end $$;
do $$ begin create role service_role nologin; exception when duplicate_object then null; end $$;
-- Match the hosted default grants that a PUBLIC-only revoke does not remove.
alter default privileges in schema public grant execute on functions to anon,authenticated,service_role;
create schema auth;
create table auth.users(id uuid primary key, email text);
create table auth.sessions(id uuid primary key, user_id uuid references auth.users(id));
create function auth.uid() returns uuid language sql stable as $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
create function auth.jwt() returns jsonb language sql stable as $$ select coalesce(nullif(current_setting('request.jwt.claims',true),''),'{}')::jsonb $$;
grant usage on schema auth to authenticated,anon;
grant execute on function auth.uid(),auth.jwt() to authenticated,anon;
`
export const ids = {
  a: '10000000-0000-4000-8000-000000000001',
  b: '10000000-0000-4000-8000-000000000002',
  admin: '20000000-0000-4000-8000-000000000001',
  agent: '20000000-0000-4000-8000-000000000002',
  viewer: '20000000-0000-4000-8000-000000000003',
  outsider: '20000000-0000-4000-8000-000000000004',
  ticketA: '30000000-0000-4000-8000-000000000001',
  ticketB: '30000000-0000-4000-8000-000000000002',
  docA: '40000000-0000-4000-8000-000000000001',
  docB: '40000000-0000-4000-8000-000000000002',
}
export async function seed(db) {
  await db.exec(`insert into auth.users values ('${ids.admin}','admin@nexus.test'),('${ids.agent}','agent@nexus.test'),('${ids.viewer}','viewer@nexus.test'),('${ids.outsider}','outsider@nexus.test');
    insert into public.tenants(id,name,slug) values ('${ids.a}','Acme Corporation','acme'),('${ids.b}','Nova Technologies','nova');
    insert into public.memberships(tenant_id,user_id,role) values ('${ids.a}','${ids.admin}','admin'),('${ids.b}','${ids.admin}','admin'),('${ids.a}','${ids.agent}','agent'),('${ids.a}','${ids.viewer}','viewer');
    insert into public.tickets(id,tenant_id,subject,description,created_by,customer_name) values ('${ids.ticketA}','${ids.a}','Delivery delayed for five days','My order has been delayed for five days. Please check the delivery status.','${ids.admin}','Alex Morgan'),('${ids.ticketB}','${ids.b}','Private Nova ticket','This message belongs only to Nova Technologies.','${ids.admin}','Nova Customer');
    insert into public.knowledge_docs(id,tenant_id,title,content,document_type,created_by) values ('${ids.docA}','${ids.a}','Delivery support procedure','For delayed delivery, collect the order reference and contact the logistics team. Do not guarantee a delivery date.','policy','${ids.admin}'),('${ids.docB}','${ids.b}','Nova private policy','Nova-only private knowledge. Do not disclose to Acme.','policy','${ids.admin}');`)
}
export async function migrate(db) {
  for (const filename of (await readdir('supabase/migrations')).filter((f) => f.endsWith('.sql')).sort())
    await db.exec(await readFile(`supabase/migrations/${filename}`, 'utf8'))
}

async function main() {
  let db
  if (process.argv.includes('--native')) {
    const { default: pg } = await import('pg')
    const admin = new pg.Client({
      connectionString:
        process.env.DATABASE_TEST_URL || 'postgresql://postgres:nexus-local-only@127.0.0.1:55432/postgres',
    })
    await admin.connect()
    const database = `nexus_security_${Date.now()}`
    await admin.query(`create database ${database}`)
    const url = new URL(
      process.env.DATABASE_TEST_URL || 'postgresql://postgres:nexus-local-only@127.0.0.1:55432/postgres',
    )
    url.pathname = '/' + database
    const client = new pg.Client({ connectionString: url.toString() })
    await client.connect()
    const query = (sql, params) => client.query(sql, params)
    db = {
      query,
      exec: (sql) => query(sql),
      transaction: async (fn) => {
        await query('begin')
        try {
          const value = await fn({ query, exec: (sql) => query(sql) })
          await query('commit')
          return value
        } catch (error) {
          await query('rollback')
          throw error
        }
      },
      close: async () => {
        await client.end()
        await admin.query(`drop database ${database}`)
        await admin.end()
      },
    }
    console.log('Testing native PostgreSQL in an isolated temporary database.')
  } else db = new PGlite()
  await db.exec(shim)
  await migrate(db)
  await seed(db)
  let passed = 0
  const check = async (name, fn) => {
    await fn()
    passed++
    console.log(`PASS ${name}`)
  }
  const as = async (user, fn) =>
    db.transaction(async (tx) => {
      await tx.exec(`set local role authenticated; set local "request.jwt.claim.sub"='${user}'`)
      return fn(tx)
    })
  const denied = async (fn) => assert.rejects(fn)
  await check('all exposed tables have RLS', async () => {
    const r = await db.query(
      "select relname from pg_class c join pg_namespace n on c.relnamespace=n.oid where n.nspname='public' and c.relkind='r' and not relrowsecurity",
    )
    assert.equal(r.rows.length, 0)
  })
  await check('agent SELECT sees own tenant only', () =>
    as(ids.agent, async (tx) => {
      const r = await tx.query('select id from public.tickets')
      assert.deepEqual(
        r.rows.map((r) => r.id),
        [ids.ticketA],
      )
    }),
  )
  await check('viewer cannot INSERT', () =>
    denied(() =>
      as(ids.viewer, (tx) =>
        tx.query('insert into public.tickets(tenant_id,subject,description) values($1,$2,$3)', [
          ids.a,
          'Forbidden ticket',
          'A viewer must not be allowed to create this.',
        ]),
      ),
    ),
  )
  await check('cross-tenant INSERT rejected', () =>
    denied(() =>
      as(ids.agent, (tx) =>
        tx.query('insert into public.tickets(tenant_id,subject,description) values($1,$2,$3)', [
          ids.b,
          'Foreign ticket',
          'This should be rejected by row-level security.',
        ]),
      ),
    ),
  )
  await check('identity fields cannot be changed', () =>
    denied(() =>
      as(ids.agent, (tx) =>
        tx.query('update public.tickets set tenant_id=$1 where id=$2', [ids.b, ids.ticketA]),
      ),
    ),
  )
  await check('cross-tenant UPDATE affects no rows', () =>
    as(ids.agent, async (tx) => {
      const r = await tx.query(
        "update public.tickets set subject='Malicious edit' where id=$1 returning id",
        [ids.ticketB],
      )
      assert.equal(r.rows.length, 0)
    }),
  )
  await check('DELETE privileges denied', () =>
    denied(() => as(ids.admin, (tx) => tx.query('delete from public.tickets where id=$1', [ids.ticketA]))),
  )
  await check('cross-tenant documents excluded', () =>
    as(ids.agent, async (tx) => {
      const r = await tx.query('select id from public.knowledge_docs')
      assert.deepEqual(
        r.rows.map((r) => r.id),
        [ids.docA],
      )
    }),
  )
  await check('agent cannot manage knowledge', () =>
    as(ids.agent, async (tx) => {
      const r = await tx.query(
        "update public.knowledge_docs set title='Incorrect update' where id=$1 returning id",
        [ids.docA],
      )
      assert.equal(r.rows.length, 0)
    }),
  )
  await check('memberships do not recurse or reveal other members to agent', () =>
    as(ids.agent, async (tx) => {
      const r = await tx.query('select user_id from public.memberships')
      assert.deepEqual(
        r.rows.map((r) => r.user_id),
        [ids.agent],
      )
    }),
  )
  await check('admin sees directory; viewer cannot read audit', async () => {
    await as(ids.admin, async (tx) =>
      assert.equal((await tx.query('select * from public.memberships')).rows.length, 4),
    )
    await as(ids.viewer, async (tx) =>
      assert.equal((await tx.query('select * from public.audit_logs')).rows.length, 0),
    )
  })
  await check('valid INSERT + audit are atomic', () =>
    as(ids.agent, async (tx) => {
      const r = await tx.query(
        "insert into public.tickets(tenant_id,subject,description) values($1,'测试工单','客户需要帮助处理物流延迟问题，请协助查询。') returning *",
        [ids.a],
      )
      assert.equal(r.rows[0].created_by, ids.agent)
      assert.equal(r.rows[0].status, 'open')
    }),
  )
  await check('invalid ticket lifecycle is rejected', () =>
    denied(() =>
      as(ids.agent, (tx) => tx.query("update public.tickets set status='closed' where id=$1", [ids.ticketA])),
    ),
  )
  await check('valid lifecycle transition succeeds', () =>
    as(ids.agent, (tx) =>
      tx.query("update public.tickets set status='in_progress' where id=$1", [ids.ticketA]),
    ),
  )
  let run
  await check('analysis is atomic and idempotent', () =>
    as(ids.agent, async (tx) => {
      run = (
        await tx.query('select public.create_analysis($1,$2,$3,$4) as run', [
          ids.a,
          ids.ticketA,
          'same-key',
          'fixture',
        ])
      ).rows[0].run
      const again = (
        await tx.query('select public.create_analysis($1,$2,$3,$4) as run', [
          ids.a,
          ids.ticketA,
          'same-key',
          'fixture',
        ])
      ).rows[0].run
      assert.equal(run.id, again.id)
      assert.equal(run.ticket_snapshot, undefined)
    }),
  )
  await check('changed idempotency payload conflicts', () =>
    denied(() =>
      as(ids.agent, (tx) =>
        tx.query('select public.create_analysis($1,$2,$3,$4)', [
          ids.a,
          ids.ticketA,
          'same-key',
          'different-model',
        ]),
      ),
    ),
  )
  await check('foreign ticket analysis rejected', () =>
    denied(() =>
      as(ids.agent, (tx) =>
        tx.query('select public.create_analysis($1,$2,$3,$4)', [ids.a, ids.ticketB, 'foreign', 'fixture']),
      ),
    ),
  )
  await check('viewer analysis rejected in DB', () =>
    denied(() =>
      as(ids.viewer, (tx) =>
        tx.query('select public.create_analysis($1,$2,$3,$4)', [ids.a, ids.ticketA, 'viewer', 'fixture']),
      ),
    ),
  )
  await check('authenticated cannot directly write runs or results', async () => {
    await denied(() =>
      as(ids.agent, (tx) =>
        tx.query("update public.analysis_runs set status='succeeded' where id=$1", [run.id]),
      ),
    )
    await denied(() =>
      as(ids.admin, (tx) =>
        tx.query('insert into public.ai_results(tenant_id,run_id) values($1,$2)', [ids.a, run.id]),
      ),
    )
  })
  const insertResult = async (tenant, runId, sources) =>
    db.query(
      `insert into public.ai_results(tenant_id,run_id,category,suggested_priority,sentiment,summary,suggested_reply,reasoning_summary,source_document_ids)
    values($1,$2,'delivery','normal','neutral','Delivery issue','Please provide your order reference.','Delivery support reference',$3) returning *`,
      [tenant, runId, JSON.stringify(sources)],
    )
  await check('composite FK rejects cross-tenant result', () => denied(() => insertResult(ids.b, run.id, [])))
  await check('foreign citation rejected', () => denied(() => insertResult(ids.a, run.id, [ids.docB])))
  await insertResult(ids.a, run.id, [ids.docA])
  await check('one result per run', () => denied(() => insertResult(ids.a, run.id, [])))
  await check('viewer cannot review', () =>
    denied(() =>
      as(ids.viewer, (tx) =>
        tx.query('select public.review_analysis($1,$2,$3)', [ids.a, run.id, 'approved']),
      ),
    ),
  )
  await check('first review final; identical repeat is idempotent', async () => {
    await as(ids.agent, async (tx) => {
      const a = (await tx.query('select public.review_analysis($1,$2,$3) as r', [ids.a, run.id, 'approved']))
        .rows[0].r
      const b = (await tx.query('select public.review_analysis($1,$2,$3) as r', [ids.a, run.id, 'approved']))
        .rows[0].r
      assert.equal(a.reviewed_at, b.reviewed_at)
    })
    await denied(() =>
      as(ids.agent, (tx) => tx.query('select public.review_analysis($1,$2,$3)', [ids.a, run.id, 'rejected'])),
    )
    assert.equal(
      (await db.query("select * from public.audit_logs where action='result.approved'")).rows.length,
      1,
    )
  })
  await check('membership revocation applies immediately', async () => {
    await db.query('update public.memberships set is_active=false where tenant_id=$1 and user_id=$2', [
      ids.a,
      ids.agent,
    ])
    await as(ids.agent, async (tx) =>
      assert.equal((await tx.query('select * from public.tickets')).rows.length, 0),
    )
  })
  await check('anon cannot execute privileged helpers', async () => {
    const grants = await db.query(`
      select p.proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace
      where n.nspname='public' and p.proname in ('create_analysis','review_analysis','session_active')
      and (has_function_privilege('anon',p.oid,'EXECUTE')
        or has_function_privilege('service_role',p.oid,'EXECUTE'))
    `)
    assert.equal(grants.rows.length, 0)
    await denied(() =>
      db.transaction(async (tx) => {
        await tx.exec('set local role anon')
        await tx.query('select public.create_analysis($1,$2,$3,$4)', [ids.a, ids.ticketA, 'anon', 'fixture'])
      }),
    )
  })
  await check('terminal run immutable', async () => {
    await db.query("update public.analysis_runs set status='processing' where id=$1", [run.id])
    await db.query("update public.analysis_runs set status='succeeded' where id=$1", [run.id])
    await denied(() => db.query("update public.analysis_runs set status='processing' where id=$1", [run.id]))
  })
  await check('daily AI quota follows UTC even in a different session timezone', async () => {
    await db.query('update public.memberships set is_active=true where tenant_id=$1 and user_id=$2', [
      ids.a,
      ids.agent,
    ])
    const hour = Number(
      (await db.query("select extract(hour from now() at time zone 'UTC') as hour")).rows[0].hour,
    )
    await db.query(
      `insert into public.analysis_runs(tenant_id,ticket_id,initiated_by,status,model_id,request_hash,ticket_snapshot,created_at)
      select $1,$2,$3,'failed','fixture','quota-fixture','{}',
      (date_trunc('day',now() at time zone 'UTC') at time zone 'UTC')+
      case when extract(hour from now() at time zone 'UTC')>=1 then interval '1 second' else interval '-30 minutes' end
      from generate_series(1,200)`,
      [ids.a, ids.ticketA, ids.agent],
    )
    const execute = () =>
      as(ids.agent, async (tx) => {
        await tx.exec(hour >= 1 ? "set local time zone 'Etc/GMT+1'" : "set local time zone 'Etc/GMT-1'")
        return tx.query('select public.create_analysis($1,$2,$3,$4)', [
          ids.a,
          ids.ticketA,
          'utc-budget',
          'fixture',
        ])
      })
    if (hour >= 1) await assert.rejects(execute, (error) => error.message.includes('USAGE_LIMIT'))
    else await execute()
  })
  console.log(`${passed} PostgreSQL RLS/constraint checks passed.`)
  await db.close()
}
if (process.argv[1]?.endsWith('test-database.mjs')) await main()
