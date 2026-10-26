import contextlib
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query, Request
from redis.exceptions import RedisError

from app.auth.security import Identity, identity
from app.core.config import get_settings
from app.repositories.data import DOC_FIELDS, RUN_FIELDS, TICKET_FIELDS, Repository, search_filter
from app.schemas.models import (
    AIResult,
    AnalysisAccepted,
    Audit,
    Knowledge,
    KnowledgeCreate,
    KnowledgePatch,
    Member,
    Page,
    Principal,
    Priority,
    Run,
    Tenant,
    Ticket,
    TicketCreate,
    TicketPatch,
    TicketStatus,
)
from app.services.workspace import Workspace, workspace

router = APIRouter(prefix="/api/v1")


@router.get("/me", response_model=Principal, tags=["Identity"])
async def me(actor: Identity = Depends(identity)):
    return actor.principal


@router.get("/me/tenants", response_model=list[Tenant], tags=["Identity"])
async def tenants(actor: Identity = Depends(identity)):
    repo = Repository(actor.token)
    try:
        rows = await repo.call(
            "GET",
            "memberships",
            {
                "user_id": f"eq.{actor.principal.id}",
                "is_active": "eq.true",
                "select": "role,tenants(id,name,slug)",
            },
        )
        return [{**row["tenants"], "role": row["role"]} for row in rows if row["tenants"]]
    finally:
        await repo.close()


@router.get("/tenants/{tid}/tickets", response_model=Page[Ticket], tags=["Tickets"])
async def tickets(
    ctx: Workspace = Depends(workspace),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None, max_length=1000),
    status: TicketStatus | None = None,
    priority: Priority | None = None,
    q: str = Query("", max_length=200),
):
    filters = {}
    if status:
        filters["status"] = f"eq.{status}"
    if priority:
        filters["priority"] = f"eq.{priority}"
    if q.strip():
        filters["subject"] = search_filter(q.strip())
    return await ctx.repo.page("tickets", ctx.tenant_id, limit, cursor, TICKET_FIELDS, filters)


@router.post("/tenants/{tid}/tickets", response_model=Ticket, status_code=201, tags=["Tickets"])
async def create_ticket(body: TicketCreate, ctx: Workspace = Depends(workspace)):
    ctx.require_write()
    rows = await ctx.repo.call(
        "POST", "tickets", body={**body.model_dump(mode="json"), "tenant_id": str(ctx.tenant_id)}
    )
    return rows[0]


@router.get("/tenants/{tid}/tickets/{ticket_id}", response_model=Ticket, tags=["Tickets"])
async def ticket(ticket_id: UUID, ctx: Workspace = Depends(workspace)):
    return await ctx.repo.one("tickets", ctx.tenant_id, ticket_id, TICKET_FIELDS)


@router.patch("/tenants/{tid}/tickets/{ticket_id}", response_model=Ticket, tags=["Tickets"])
async def update_ticket(ticket_id: UUID, body: TicketPatch, ctx: Workspace = Depends(workspace)):
    ctx.require_write()
    await ctx.repo.one("tickets", ctx.tenant_id, ticket_id, TICKET_FIELDS)
    rows = await ctx.repo.call(
        "PATCH",
        "tickets",
        {"id": f"eq.{ticket_id}", "tenant_id": f"eq.{ctx.tenant_id}"},
        body.model_dump(mode="json", exclude_unset=True),
    )
    if not rows:
        from app.core.errors import not_found

        raise not_found()
    return rows[0]


@router.post(
    "/tenants/{tid}/tickets/{ticket_id}/analyze",
    response_model=AnalysisAccepted,
    status_code=202,
    tags=["Analysis"],
)
async def analyze(
    ticket_id: UUID,
    request: Request,
    ctx: Workspace = Depends(workspace),
    idempotency_key: str | None = Header(None, min_length=1, max_length=150),
):
    ctx.require_write()
    run = await ctx.repo.call(
        "POST",
        "rpc/create_analysis",
        body={
            "tid": str(ctx.tenant_id),
            "ticket": str(ticket_id),
            "idem": idempotency_key or str(uuid4()),
            "model": get_settings().llm_model,
        },
    )
    # Durable queued row is the outbox. Reconciliation repairs Redis outages.
    with contextlib.suppress(RedisError):
        await request.app.state.redis.xadd(
            "nexus:jobs", {"run_id": run["id"], "tenant_id": str(ctx.tenant_id)}
        )
    return {"run_id": run["id"], "status": run["status"], "created_at": run["created_at"]}


@router.get("/tenants/{tid}/runs", response_model=Page[Run], tags=["Analysis"])
async def runs(
    ctx: Workspace = Depends(workspace),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None, max_length=1000),
    ticket_id: UUID | None = None,
):
    return await ctx.repo.page(
        "analysis_runs",
        ctx.tenant_id,
        limit,
        cursor,
        RUN_FIELDS,
        {"ticket_id": f"eq.{ticket_id}"} if ticket_id else {},
    )


@router.get("/tenants/{tid}/runs/{run_id}", response_model=Run, tags=["Analysis"])
async def run(run_id: UUID, ctx: Workspace = Depends(workspace)):
    return await ctx.repo.one("analysis_runs", ctx.tenant_id, run_id, RUN_FIELDS)


@router.get("/tenants/{tid}/runs/{run_id}/result", response_model=AIResult, tags=["Analysis"])
async def result(run_id: UUID, ctx: Workspace = Depends(workspace)):
    return await ctx.repo.one("ai_results", ctx.tenant_id, run_id, key="run_id")


@router.post("/tenants/{tid}/runs/{run_id}/approve", response_model=AIResult, tags=["Review"])
async def approve(run_id: UUID, ctx: Workspace = Depends(workspace)):
    ctx.require_write()
    return await ctx.repo.call(
        "POST",
        "rpc/review_analysis",
        body={"tid": str(ctx.tenant_id), "run": str(run_id), "decision": "approved"},
    )


@router.post("/tenants/{tid}/runs/{run_id}/reject", response_model=AIResult, tags=["Review"])
async def reject(run_id: UUID, ctx: Workspace = Depends(workspace)):
    ctx.require_write()
    return await ctx.repo.call(
        "POST",
        "rpc/review_analysis",
        body={"tid": str(ctx.tenant_id), "run": str(run_id), "decision": "rejected"},
    )


@router.get("/tenants/{tid}/knowledge", response_model=Page[Knowledge], tags=["Knowledge"])
async def knowledge(
    ctx: Workspace = Depends(workspace),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None, max_length=1000),
    q: str = Query("", max_length=200),
):
    return await ctx.repo.page(
        "knowledge_docs",
        ctx.tenant_id,
        limit,
        cursor,
        DOC_FIELDS,
        {"title": search_filter(q)} if q else {},
    )


@router.post(
    "/tenants/{tid}/knowledge", response_model=Knowledge, status_code=201, tags=["Knowledge"]
)
async def create_document(body: KnowledgeCreate, ctx: Workspace = Depends(workspace)):
    ctx.require_admin()
    return (
        await ctx.repo.call(
            "POST",
            "knowledge_docs",
            params={"select": DOC_FIELDS},
            body={**body.model_dump(mode="json"), "tenant_id": str(ctx.tenant_id)},
        )
    )[0]


@router.get("/tenants/{tid}/knowledge/{document_id}", response_model=Knowledge, tags=["Knowledge"])
async def document(document_id: UUID, ctx: Workspace = Depends(workspace)):
    return await ctx.repo.one("knowledge_docs", ctx.tenant_id, document_id, DOC_FIELDS)


@router.patch(
    "/tenants/{tid}/knowledge/{document_id}", response_model=Knowledge, tags=["Knowledge"]
)
async def update_document(
    document_id: UUID, body: KnowledgePatch, ctx: Workspace = Depends(workspace)
):
    ctx.require_admin()
    await ctx.repo.one("knowledge_docs", ctx.tenant_id, document_id, DOC_FIELDS)
    rows = await ctx.repo.call(
        "PATCH",
        "knowledge_docs",
        {"id": f"eq.{document_id}", "tenant_id": f"eq.{ctx.tenant_id}", "select": DOC_FIELDS},
        body.model_dump(mode="json", exclude_unset=True),
    )
    if not rows:
        from app.core.errors import not_found

        raise not_found()
    return rows[0]


@router.get("/tenants/{tid}/members", response_model=list[Member], tags=["Organization"])
async def members(ctx: Workspace = Depends(workspace)):
    ctx.require_admin()
    return await ctx.repo.call(
        "GET",
        "memberships",
        {
            "tenant_id": f"eq.{ctx.tenant_id}",
            "select": "user_id,role,is_active,created_at",
            "order": "created_at.asc",
        },
    )


@router.get("/tenants/{tid}/audit", response_model=Page[Audit], tags=["Organization"])
async def audit(
    ctx: Workspace = Depends(workspace),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(None, max_length=1000),
):
    ctx.require_admin()
    return await ctx.repo.page("audit_logs", ctx.tenant_id, limit, cursor)
