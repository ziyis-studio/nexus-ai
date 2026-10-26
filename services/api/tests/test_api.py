import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import respx
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.repositories.data import Repository, search_filter
from app.schemas.models import KnowledgePatch, TicketCreate, TicketPatch
from httpx import Response
from pydantic import ValidationError

TID, UID, ACTOR = str(uuid4()), str(uuid4()), str(uuid4())
NOW = datetime.now(UTC).isoformat()
TICKET = {
    "id": UID,
    "tenant_id": TID,
    "subject": "Delayed delivery",
    "description": "Order delayed for five days, please check.",
    "customer_name": None,
    "customer_email": None,
    "external_reference": None,
    "created_by": ACTOR,
    "status": "open",
    "priority": "normal",
    "created_at": NOW,
    "updated_at": NOW,
}
RUN = {
    "id": UID,
    "tenant_id": TID,
    "ticket_id": UID,
    "initiated_by": ACTOR,
    "status": "queued",
    "model_id": "fixture",
    "attempt_count": 0,
    "created_at": NOW,
    "started_at": None,
    "completed_at": None,
    "error_code": None,
    "error_message": None,
}


@pytest.mark.parametrize(
    "body",
    [
        {"subject": "x", "description": "A valid description"},
        {"subject": "Valid subject", "description": "short"},
        {
            "subject": "Valid subject",
            "description": "A valid description",
            "customer_email": "invalid",
        },
        {"subject": "A" * 201, "description": "A valid description"},
        {"subject": "Valid subject", "description": "A" * 10001},
        {"subject": "   ", "description": "A valid description"},
    ],
)
def test_ticket_validation(body):
    with pytest.raises(ValidationError):
        TicketCreate.model_validate(body)


@pytest.mark.parametrize(
    "model,body",
    [
        (TicketPatch, {}),
        (TicketPatch, {"status": None}),
        (TicketPatch, {"tenant_id": TID}),
        (KnowledgePatch, {}),
        (KnowledgePatch, {"content": None}),
    ],
)
def test_invalid_patch(model, body):
    with pytest.raises(ValidationError):
        model.model_validate(body)


def test_unicode_and_injection_are_plain_content():
    value = TicketCreate(
        subject="订单延迟问题", description="客户请求退款。'; DROP TABLE tickets; --"
    )
    assert "DROP TABLE" in value.description
    assert search_filter("100%_rate*") == "ilike.*100\\%\\_rate\\**"


@respx.mock
def test_create_ticket(client, token):
    respx.get(get_settings().rest_url + "/memberships").mock(
        return_value=Response(200, json=[{"role": "agent"}])
    )
    route = respx.post(get_settings().rest_url + "/tickets").mock(
        return_value=Response(201, json=[TICKET])
    )
    response = client.post(
        f"/api/v1/tenants/{TID}/tickets",
        json={"subject": TICKET["subject"], "description": TICKET["description"]},
        headers={"Authorization": "Bearer " + token},
    )
    assert response.status_code == 201
    body = json.loads(route.calls.last.request.content)
    assert body["tenant_id"] == TID and "created_by" not in body and "status" not in body


@respx.mock
def test_analysis_accepted_even_when_redis_down(client, token):
    respx.get(get_settings().rest_url + "/memberships").mock(
        return_value=Response(200, json=[{"role": "agent"}])
    )
    route = respx.post(get_settings().rest_url + "/rpc/create_analysis").mock(
        return_value=Response(200, json=RUN)
    )
    response = client.post(
        f"/api/v1/tenants/{TID}/tickets/{UID}/analyze",
        headers={"Authorization": "Bearer " + token, "Idempotency-Key": "persisted-key"},
    )
    assert response.status_code == 202
    assert response.json()["run_id"] == UID
    assert json.loads(route.calls.last.request.content)["idem"] == "persisted-key"


@pytest.mark.parametrize(
    "db_code,message,status,code",
    [
        ("23505", "IDEMPOTENCY_CONFLICT", 409, "IDEMPOTENCY_CONFLICT"),
        ("23505", "REVIEW_FINAL", 409, "REVIEW_FINAL"),
        ("23514", "INVALID_TRANSITION", 400, "INVALID_TRANSITION"),
        ("P0001", "USAGE_LIMIT", 429, "USAGE_LIMIT"),
        ("42501", "denied", 403, "TENANT_ACCESS_DENIED"),
        ("P0002", "NOT_FOUND", 404, "NOT_FOUND"),
        ("other", "internal sensitive details", 503, "DATABASE_UNAVAILABLE"),
    ],
)
@respx.mock
async def test_error_mapping(db_code, message, status, code):
    respx.get(get_settings().rest_url + "/tickets").mock(
        return_value=Response(400, json={"code": db_code, "message": message})
    )
    repo = Repository("synthetic-token")
    try:
        with pytest.raises(AppError) as error:
            await repo.call("GET", "tickets")
        assert error.value.status == status and error.value.code == code
        assert "sensitive" not in error.value.message
    finally:
        await repo.close()


@respx.mock
async def test_cursor_pagination_and_tenant_binding():
    second = {**TICKET, "id": str(uuid4())}
    route = respx.get(get_settings().rest_url + "/tickets").mock(
        return_value=Response(200, json=[TICKET, second])
    )
    repo = Repository("synthetic-token")
    try:
        page = await repo.page("tickets", TID, 1, None)
        assert len(page["items"]) == 1 and page["next_cursor"]
        await repo.page("tickets", TID, 1, page["next_cursor"])
        assert "id.lt." in route.calls.last.request.url.params["or"]
        with pytest.raises(AppError):
            await repo.page("tickets", str(uuid4()), 1, page["next_cursor"])
        with pytest.raises(AppError):
            await repo.page("tickets", TID, 1, "not valid base64")
    finally:
        await repo.close()


def test_production_rejects_fixture_and_insecure_configuration():
    with pytest.raises(ValidationError):
        Settings(environment="production", llm_provider="fixture")
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            llm_provider="openai",
            openai_api_key="test",
            supabase_url="http://localhost",
        )
    with pytest.raises(ValidationError):
        Settings(lease_seconds=100, job_deadline=180)


def test_health_and_request_validation_envelope(client):
    assert client.get("/health/live").json() == {"status": "ok"}
    response = client.get("/api/v1/me")
    assert set(response.json()) == {"error"}


def test_contract_matches_application(client):
    from pathlib import Path

    import yaml

    assert (
        yaml.safe_load(Path("contracts/openapi.yaml").read_text(encoding="utf-8"))
        == client.get("/openapi.json").json()
    )
