import os
from uuid import UUID, uuid4

import httpx
import psycopg
from app.core.config import Settings

from services.worker.ai import validate_output
from services.worker.repository import WorkerRepository

DB = os.getenv(
    "INTEGRATION_DATABASE_URL", "postgresql://postgres:nexus-local-only@127.0.0.1:55432/postgres"
)
TID = UUID("10000000-0000-4000-8000-000000000001")
OTHER = UUID("10000000-0000-4000-8000-000000000002")
TICKET = UUID("30000000-0000-4000-8000-000000000001")
ADMIN = UUID("20000000-0000-4000-8000-000000000001")


async def test_lease_recovery_fences_old_worker_and_persists_one_result():
    run_id = uuid4()
    with psycopg.connect(DB) as db:
        db.execute(
            """insert into public.analysis_runs(id,tenant_id,ticket_id,initiated_by,model_id,request_hash,ticket_snapshot,created_at)
          values(%s,%s,%s,%s,'fixture','integration','{"subject":"Delivery delay","description":"My order is delayed for five days."}',now()+interval '1 hour')""",
            (run_id, TID, TICKET, ADMIN),
        )
    repo = WorkerRepository(Settings(environment="test", database_url=DB))
    await repo.open()
    try:
        assert await repo.claim(OTHER, run_id) is None
        first = await repo.claim(TID, run_id)
        assert first and await repo.allowed(first)
        assert await repo.claim(TID, run_id) is None
        documents = await repo.documents(TID, first["ticket_snapshot"])
        assert documents and all("Nova" not in d["title"] for d in documents)
        assert (await repo.attempt(first))["attempt_count"] == 1
        with psycopg.connect(DB) as db:
            db.execute(
                "update public.analysis_runs set worker_lease_until=now()-interval '1 second' where id=%s",
                (run_id,),
            )
        second = await repo.claim(TID, run_id)
        assert second["lease_token"] != first["lease_token"]
        output = validate_output(
            {
                "category": "delivery",
                "suggested_priority": "normal",
                "sentiment": "neutral",
                "summary": "Delivery status requested",
                "suggested_reply": "Please provide the order reference for our team to verify.",
                "needs_human_review": True,
                "reasoning_summary": "Delivery support procedure applies.",
                "source_document_ids": [documents[0]["id"]],
            },
            documents,
        )
        assert await repo.finish(first, output) is False
        assert await repo.finish(second, output) is True
        assert await repo.finish(second, output) is False
        assert await repo.terminal(TID, run_id) is True
        with psycopg.connect(DB) as db:
            assert (
                db.execute(
                    "select count(*) from public.ai_results where run_id=%s", (run_id,)
                ).fetchone()[0]
                == 1
            )
            assert (
                db.execute(
                    "select status from public.analysis_runs where id=%s", (run_id,)
                ).fetchone()[0]
                == "succeeded"
            )
    finally:
        await repo.close()


def login(client, email):
    response = client.post(
        os.getenv("INTEGRATION_AUTH_URL", "http://127.0.0.1:54321")
        + "/auth/v1/token?grant_type=password",
        json={"email": email, "password": os.getenv("E2E_PASSWORD", "Nexus-demo-2026!")},
        headers={"apikey": os.getenv("INTEGRATION_PUBLISHABLE_KEY", "sandbox-public-key")},
    )
    response.raise_for_status()
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_real_api_isolation_and_viewer_permissions():
    with httpx.Client(
        base_url=os.getenv("INTEGRATION_API_URL", "http://127.0.0.1:8000"), timeout=15
    ) as client:
        headers = login(client, "agent@nexus.test")
        assert client.get(f"/api/v1/tenants/{OTHER}/tickets", headers=headers).status_code == 403
        foreign = "30000000-0000-4000-8000-000000000002"
        assert (
            client.get(f"/api/v1/tenants/{TID}/tickets/{foreign}", headers=headers).status_code
            == 404
        )
        assert (
            client.patch(
                f"/api/v1/tenants/{TID}/tickets/{foreign}",
                headers=headers,
                json={"subject": "Malicious request"},
            ).status_code
            == 404
        )
        assert (
            client.post(
                f"/api/v1/tenants/{TID}/tickets/{foreign}/analyze", headers=headers
            ).status_code
            == 404
        )
        viewer = login(client, "viewer@nexus.test")
        assert (
            client.post(
                f"/api/v1/tenants/{TID}/tickets",
                headers=viewer,
                json={"subject": "Viewer write", "description": "This action must be forbidden."},
            ).status_code
            == 403
        )
        assert client.get(f"/api/v1/tenants/{TID}/members", headers=viewer).status_code == 403


def test_real_api_idempotency_and_stable_pagination():
    with httpx.Client(
        base_url=os.getenv("INTEGRATION_API_URL", "http://127.0.0.1:8000"), timeout=15
    ) as client:
        headers = login(client, "agent@nexus.test")
        ticket = client.post(
            f"/api/v1/tenants/{TID}/tickets",
            headers=headers,
            json={
                "subject": "Integration delivery request",
                "description": "Customer requests help with an order delayed for five days.",
            },
        )
        assert ticket.status_code == 201
        key = str(uuid4())
        a = client.post(
            f"/api/v1/tenants/{TID}/tickets/{ticket.json()['id']}/analyze",
            headers={**headers, "Idempotency-Key": key},
        )
        b = client.post(
            f"/api/v1/tenants/{TID}/tickets/{ticket.json()['id']}/analyze",
            headers={**headers, "Idempotency-Key": key},
        )
        assert a.status_code == b.status_code == 202 and a.json()["run_id"] == b.json()["run_id"]
        first = client.get(f"/api/v1/tenants/{TID}/tickets?limit=2", headers=headers).json()
        second = client.get(
            f"/api/v1/tenants/{TID}/tickets",
            params={"limit": 2, "cursor": first["next_cursor"]},
            headers=headers,
        ).json()
        assert not ({t["id"] for t in first["items"]} & {t["id"] for t in second["items"]})
