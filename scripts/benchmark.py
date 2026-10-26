"""Reproducible, isolated 10,000-ticket SQL benchmark. Never touches app data."""

import json
import os
import platform
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql

url = os.getenv(
    "BENCHMARK_DATABASE_URL", "postgresql://postgres:nexus-local-only@127.0.0.1:55432/postgres"
)
name = "nexus_perf_" + str(int(time.time()))
admin = psycopg.connect(url, autocommit=True)
admin.execute(sql.SQL("create database {}").format(sql.Identifier(name)))
kwargs = psycopg.conninfo.conninfo_to_dict(url)
kwargs["dbname"] = name
db = psycopg.connect(**kwargs, autocommit=True)
try:
    db.execute(Path("scripts/fixtures/auth.sql").read_text())
    for migration in sorted(Path("supabase/migrations").glob("*.sql")):
        db.execute(migration.read_text())
    a, b, user, agent, viewer = [uuid4() for _ in range(5)]
    db.execute(
        "insert into auth.users(id,email) values(%s,%s),(%s,%s),(%s,%s)",
        (user, "admin@perf.test", agent, "agent@perf.test", viewer, "viewer@perf.test"),
    )
    db.execute(
        "insert into public.tenants(id,name,slug) values(%s,'Tenant A','perf-a'),(%s,'Tenant B','perf-b')",
        (a, b),
    )
    db.execute(
        "insert into public.memberships(tenant_id,user_id,role) values(%s,%s,'admin'),(%s,%s,'agent'),(%s,%s,'viewer')",
        (a, user, a, agent, a, viewer),
    )
    db.execute(
        """insert into public.tickets(tenant_id,subject,description,status,priority,created_by,created_at)
      select case when n%%2=0 then %s::uuid else %s::uuid end,'Synthetic ticket '||n,
      'Synthetic delivery request for repeatable SQL performance validation.',
      (array['open','in_progress','resolved','closed'])[1+(n%%4)],
      (array['normal','high','urgent','low'])[1+(n%%4)],%s,now()-n*interval '1 second' from generate_series(1,10000)n""",
        (a, b, user),
    )
    db.execute(
        """insert into public.analysis_runs(tenant_id,ticket_id,initiated_by,model_id,request_hash,ticket_snapshot)
      select tenant_id,id,%s,'fixture','benchmark','{}' from public.tickets limit 200""",
        (user,),
    )
    db.execute(
        "insert into public.knowledge_docs(tenant_id,title,content,document_type,created_by) select %s,'Delivery policy '||n,'Collect order details and contact the delivery support team.','policy',%s from generate_series(1,30)n",
        (a, user),
    )
    db.execute("analyze")
    queries = {
        "ticket_list": (
            "select id,subject,status,priority from public.tickets where tenant_id=%s order by created_at desc,id desc limit 20",
            (a,),
        ),
        "status_filter": (
            "select id,subject,status from public.tickets where tenant_id=%s and status='open' order by created_at desc,id desc limit 20",
            (a,),
        ),
        "membership": (
            "select role from public.memberships where user_id=%s and tenant_id=%s and is_active",
            (user, a),
        ),
        "execution_history": (
            "select id,status from public.analysis_runs where tenant_id=%s order by created_at desc,id desc limit 20",
            (a,),
        ),
        "knowledge_retrieval": (
            "select id from public.knowledge_docs where tenant_id=%s and is_active and search_vector @@ websearch_to_tsquery('simple','delivery') limit 4",
            (a,),
        ),
    }

    def measure(connection, query, args):
        values = []
        for _ in range(60):
            start = time.perf_counter()
            connection.execute(query, args).fetchall()
            values.append((time.perf_counter() - start) * 1000)
        values.sort()
        return {
            "median_ms": round(statistics.median(values), 3),
            "p95_ms": round(values[int(len(values) * 0.95) - 1], 3),
            "samples": len(values),
        }

    measurements = {key: measure(db, *value) for key, value in queries.items()}
    plans = {
        key: db.execute("explain(analyze,buffers,format json) " + query, args).fetchone()[0]
        for key, (query, args) in queries.items()
    }
    db.execute("drop index public.tickets_status_page")
    before = db.execute(
        "explain(analyze,buffers,format json) " + queries["status_filter"][0],
        queries["status_filter"][1],
    ).fetchone()[0]
    db.execute(
        "create index tickets_status_page on public.tickets(tenant_id,status,created_at desc,id desc)"
    )
    after = db.execute(
        "explain(analyze,buffers,format json) " + queries["status_filter"][0],
        queries["status_filter"][1],
    ).fetchone()[0]

    def concurrent_sample(_):
        with psycopg.connect(**kwargs) as connection:
            return measure(connection, *queries["ticket_list"])

    with ThreadPoolExecutor(max_workers=10) as pool:
        concurrent = list(pool.map(concurrent_sample, range(10)))
    output = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "postgresql": db.execute("select version()").fetchone()[0],
            "cpu": platform.processor(),
            "cpu_count": os.cpu_count(),
            "transport": "loopback native PostgreSQL",
            "auth": "synthetic auth schema; not hosted Supabase",
        },
        "tickets": 10000,
        "tenants": 2,
        "roles": 3,
        "measurements": measurements,
        "ten_concurrent_clients": concurrent,
        "status_index_comparison": {"before": before, "after": after},
        "plans": plans,
    }
    Path("docs/evidence").mkdir(exist_ok=True)
    Path("docs/evidence/sql-benchmark.json").write_text(
        json.dumps(output, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "measurements": measurements,
                "before_execution_ms": before[0]["Execution Time"],
                "after_execution_ms": after[0]["Execution Time"],
                "max_concurrent_client_p95_ms": max(row["p95_ms"] for row in concurrent),
            },
            indent=2,
        )
    )
finally:
    db.close()
    admin.execute(sql.SQL("drop database {}").format(sql.Identifier(name)))
    admin.close()
