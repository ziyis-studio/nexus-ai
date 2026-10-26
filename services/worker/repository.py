import re
from uuid import UUID, uuid4

from app.core.config import Settings
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool


class WorkerRepository:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.pool = AsyncConnectionPool(
            settings.database_url,
            min_size=1,
            max_size=settings.worker_concurrency + 2,
            open=False,
            kwargs={"row_factory": dict_row},
            configure=self.configure,
        )

    async def configure(self, connection):
        await connection.execute("set role nexus_worker")
        await connection.commit()

    async def open(self):
        await self.pool.open(wait=True, timeout=20)

    async def close(self):
        await self.pool.close()

    async def claim(self, tid: UUID, run_id: UUID):
        token = uuid4()
        async with self.pool.connection() as db:
            row = await (
                await db.execute(
                    """update public.analysis_runs set status='processing',
                lease_token=%s, worker_lease_until=now()+(%s * interval '1 second'), started_at=coalesce(started_at,now())
                where id=%s and tenant_id=%s and (status='queued' or
                (status='processing' and worker_lease_until<now())) returning *""",
                    (token, self.settings.lease_seconds, run_id, tid),
                )
            ).fetchone()
            return row

    async def allowed(self, run: dict) -> bool:
        async with self.pool.connection() as db:
            row = await (
                await db.execute(
                    """select 1 from public.memberships m join public.tickets t on t.tenant_id=m.tenant_id
                where m.tenant_id=%s and m.user_id=%s and m.is_active and m.role in ('admin','agent') and t.id=%s""",
                    (run["tenant_id"], run["initiated_by"], run["ticket_id"]),
                )
            ).fetchone()
            return bool(row)

    async def documents(self, tid: UUID, ticket: dict):
        # simple dictionary supports Unicode; a bounded substring fallback covers
        # unsegmented Chinese text. Archived/foreign documents are excluded first.
        terms = re.findall(
            r"[\w\u4e00-\u9fff]{2,}", ticket["subject"] + " " + ticket["description"]
        )[:20]
        query = " OR ".join(terms)
        if not terms:
            return []
        async with self.pool.connection() as db:
            rows = await (
                await db.execute(
                    """select id,title,left(content,2400) as content,
                ts_rank(search_vector,websearch_to_tsquery('simple',%s)) as score
                from public.knowledge_docs where tenant_id=%s and is_active and
                (search_vector @@ websearch_to_tsquery('simple',%s) or
                 exists(select 1 from unnest(%s::text[]) term where position(lower(term) in lower(title||' '||content))>0))
                order by score desc,id limit 4""",
                    (query, tid, query, terms),
                )
            ).fetchall()
            return [
                {"id": str(r["id"]), "title": r["title"], "content": r["content"]} for r in rows
            ]

    async def attempt(self, run: dict):
        async with self.pool.connection() as db:
            return await (
                await db.execute(
                    """update public.analysis_runs set attempt_count=attempt_count+1
                where id=%s and tenant_id=%s and lease_token=%s and status='processing' returning attempt_count""",
                    (run["id"], run["tenant_id"], run["lease_token"]),
                )
            ).fetchone()

    async def finish(self, run: dict, result=None, error_code=None):
        async with self.pool.connection() as db, db.transaction():
            current = await (
                await db.execute(
                    "select id from public.analysis_runs where id=%s and tenant_id=%s and status='processing' and lease_token=%s for update",
                    (run["id"], run["tenant_id"], run["lease_token"]),
                )
            ).fetchone()
            if not current:
                return False
            if result is not None:
                value = result.model_dump(mode="json")
                await db.execute(
                    """insert into public.ai_results(tenant_id,run_id,category,suggested_priority,sentiment,summary,suggested_reply,needs_human_review,reasoning_summary,source_document_ids)
                    values(%s,%s,%s,%s,%s,%s,%s,true,%s,%s) on conflict(run_id) do nothing""",
                    (
                        run["tenant_id"],
                        run["id"],
                        value["category"],
                        value["suggested_priority"],
                        value["sentiment"],
                        value["summary"],
                        value["suggested_reply"],
                        value["reasoning_summary"],
                        Jsonb(value["source_document_ids"]),
                    ),
                )
            status = "succeeded" if result is not None else "failed"
            await db.execute(
                """update public.analysis_runs set status=%s,completed_at=now(),worker_lease_until=null,
                error_code=%s,error_message=%s where id=%s and tenant_id=%s and lease_token=%s""",
                (
                    status,
                    error_code,
                    "Analysis could not be completed. Start a new run or contact an administrator."
                    if error_code
                    else None,
                    run["id"],
                    run["tenant_id"],
                    run["lease_token"],
                ),
            )
            await db.execute(
                """insert into public.audit_logs(tenant_id,actor_id,action,resource_type,resource_id,metadata)
                values(%s,%s,%s,'analysis_runs',%s,%s)""",
                (
                    run["tenant_id"],
                    run["initiated_by"],
                    "analysis." + status,
                    run["id"],
                    Jsonb({"error_code": error_code} if error_code else {}),
                ),
            )
            return True

    async def pending(self):
        async with self.pool.connection() as db:
            return await (
                await db.execute("""select id,tenant_id from public.analysis_runs where
                (status='queued' and created_at<now()-interval '5 seconds') or
                (status='processing' and worker_lease_until<now()) order by created_at limit 100""")
            ).fetchall()

    async def terminal(self, tid, run_id):
        async with self.pool.connection() as db:
            row = await (
                await db.execute(
                    "select status from public.analysis_runs where tenant_id=%s and id=%s",
                    (tid, run_id),
                )
            ).fetchone()
            return row is None or row["status"] in ("succeeded", "failed")
