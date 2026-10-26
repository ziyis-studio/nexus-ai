import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import fakeredis.aioredis
import httpx
import pytest
import respx
from app.core.config import Settings
from app.schemas.models import AIOutput
from openai import APIConnectionError, APIStatusError, RateLimitError
from pydantic import ValidationError

from services.worker.ai import InvalidOutput, generate, transient, validate_output
from services.worker.main import GROUP, STREAM, Worker


def sample_output(**changes):
    return {
        "category": "billing",
        "suggested_priority": "high",
        "sentiment": "negative",
        "summary": "Customer disputes a charge.",
        "suggested_reply": "Please provide the invoice reference so our team can investigate.",
        "needs_human_review": True,
        "reasoning_summary": "Billing question requiring verification.",
        "source_document_ids": [],
        **changes,
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"category": "invented"},
        {"suggested_priority": "critical"},
        {"sentiment": "angry"},
        {"summary": ""},
        {"summary": "x" * 2001},
        {"suggested_reply": "x" * 6001},
        {"needs_human_review": "false"},
        {"reasoning_summary": "x" * 1001},
        {"source_document_ids": ["not-a-uuid"]},
        {"unexpected": "injection"},
    ],
)
def test_output_validation(changes):
    with pytest.raises(ValidationError):
        AIOutput.model_validate(sample_output(**changes))


def test_references_must_be_grounded_and_human_review_required():
    uid = uuid4()
    with pytest.raises(InvalidOutput):
        validate_output(sample_output(source_document_ids=[str(uid)]), [])
    result = validate_output(
        sample_output(needs_human_review=False, source_document_ids=[str(uid), str(uid)]),
        [{"id": str(uid)}],
    )
    assert result.needs_human_review is True and result.source_document_ids == [uid]


def test_retry_only_transient_errors():
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    assert transient(APIConnectionError(request=request))
    assert transient(
        RateLimitError("rate limited", response=httpx.Response(429, request=request), body=None)
    )
    assert transient(
        APIStatusError("server error", response=httpx.Response(503, request=request), body=None)
    )
    assert not transient(
        APIStatusError("bad request", response=httpx.Response(400, request=request), body=None)
    )
    assert not transient(InvalidOutput())


async def test_fixture_is_explicit_and_does_not_invent_policy():
    output = await generate(
        Settings(environment="test", llm_provider="fixture"),
        {"subject": "Refund requested", "description": "客户需要退款，请核实订单。"},
        [],
        "fixture",
    )
    assert output.category == "billing" and not output.source_document_ids
    assert "verification" in output.suggested_reply
    with pytest.raises(InvalidOutput):
        await generate(
            Settings(environment="test", llm_provider="openai", openai_api_key=""),
            {"subject": "Test", "description": "Test"},
            [],
            "fixture",
        )


@respx.mock
async def test_openai_adapter_parses_structured_output_without_storing_customer_content():
    source = str(uuid4())
    document = {"id": source, "title": "Delivery policy", "content": "Collect the order reference."}
    route = respx.post("https://api.openai.com/v1/responses").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "resp_test",
                "object": "response",
                "created_at": 1793000000,
                "status": "completed",
                "model": "gpt-4.1-mini-2025-04-14",
                "output": [
                    {
                        "id": "msg_test",
                        "type": "message",
                        "status": "completed",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(sample_output(source_document_ids=[source])),
                                "annotations": [],
                            }
                        ],
                    }
                ],
                "parallel_tool_calls": False,
                "tool_choice": "auto",
                "tools": [],
            },
        )
    )
    result = await generate(
        Settings(environment="test", llm_provider="openai", openai_api_key="synthetic-key"),
        {"subject": "Invoice question", "description": "Please check my invoice."},
        [document],
        "gpt-4.1-mini-2025-04-14",
    )
    assert result.source_document_ids == [UUID(source)]
    payload = json.loads(route.calls.last.request.content)
    assert payload["store"] is False
    assert payload["text"]["format"]["type"] == "json_schema"
    assert payload["text"]["format"]["strict"] is True
    assert payload["max_output_tokens"] == 2200


@respx.mock
async def test_openai_refusal_is_a_validation_failure():
    respx.post("https://api.openai.com/v1/responses").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "resp_refused",
                "object": "response",
                "created_at": 1793000000,
                "status": "completed",
                "model": "gpt-4.1-mini-2025-04-14",
                "output": [
                    {
                        "id": "msg_refused",
                        "type": "message",
                        "status": "completed",
                        "role": "assistant",
                        "content": [{"type": "refusal", "refusal": "Cannot comply."}],
                    }
                ],
                "parallel_tool_calls": False,
                "tool_choice": "auto",
                "tools": [],
            },
        )
    )
    with pytest.raises(InvalidOutput):
        await generate(
            Settings(environment="test", llm_provider="openai", openai_api_key="synthetic-key"),
            {"subject": "Test refusal", "description": "A synthetic refusal case."},
            [],
            "gpt-4.1-mini-2025-04-14",
        )


@pytest.fixture
async def context():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await redis.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
    run = {
        "id": uuid4(),
        "tenant_id": uuid4(),
        "ticket_id": uuid4(),
        "initiated_by": uuid4(),
        "status": "processing",
        "lease_token": uuid4(),
        "attempt_count": 0,
        "model_id": "fixture",
        "started_at": datetime.now(UTC),
        "ticket_snapshot": {
            "subject": "Delayed delivery",
            "description": "My order has been delayed for five days.",
        },
    }
    repo = AsyncMock()
    repo.claim.return_value = run
    repo.allowed.return_value = True
    repo.documents.return_value = []
    repo.attempt.side_effect = [{"attempt_count": 1}, {"attempt_count": 2}, {"attempt_count": 3}]
    repo.finish.return_value = True
    repo.terminal.return_value = True
    settings = Settings(environment="test", llm_provider="fixture", llm_model="fixture")
    worker = Worker(settings, repo, redis)
    msg = await redis.xadd(STREAM, {"run_id": str(run["id"]), "tenant_id": str(run["tenant_id"])})
    await redis.xreadgroup(GROUP, "test", {STREAM: ">"}, count=1)
    yield worker, repo, redis, run, msg
    await redis.aclose()


async def test_consume_persist_ack_and_no_duplicate_execution(context):
    worker, repo, redis, run, msg = context
    payload = {"run_id": str(run["id"]), "tenant_id": str(run["tenant_id"])}
    await worker.process(msg, payload)
    assert repo.finish.call_args.args[1].category == "delivery"
    assert (await redis.xpending(STREAM, GROUP))["pending"] == 0
    repo.claim.return_value = None
    await worker.process(msg, payload)
    assert repo.finish.await_count == 1


async def test_revoked_membership_fails_without_provider(context):
    worker, repo, redis, run, msg = context
    repo.allowed.return_value = False
    with patch("services.worker.main.generate", new_callable=AsyncMock) as model:
        await worker.process(msg, {"run_id": str(run["id"]), "tenant_id": str(run["tenant_id"])})
        model.assert_not_awaited()
    assert repo.finish.call_args.args[2] == "AUTHORIZATION_REVOKED"


async def test_retry_transient_provider_failure(context):
    worker, repo, redis, run, msg = context
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    with (
        patch("services.worker.main.generate", new_callable=AsyncMock) as model,
        patch("services.worker.main.asyncio.sleep", new_callable=AsyncMock),
    ):
        model.side_effect = [
            APIConnectionError(request=request),
            AIOutput.model_validate(sample_output()),
        ]
        await worker.process(msg, {"run_id": str(run["id"]), "tenant_id": str(run["tenant_id"])})
        assert model.await_count == 2
    assert repo.finish.call_args.args[2] is None


async def test_validation_failure_is_not_retried(context):
    worker, repo, redis, run, msg = context
    with patch("services.worker.main.generate", new_callable=AsyncMock) as model:
        model.side_effect = InvalidOutput()
        await worker.process(msg, {"run_id": str(run["id"]), "tenant_id": str(run["tenant_id"])})
        assert model.await_count == 1
    assert repo.finish.call_args.args[2] == "INVALID_AI_OUTPUT"


async def test_expired_deadline_is_terminal(context):
    worker, repo, redis, run, msg = context
    run["started_at"] = datetime.now(UTC) - timedelta(seconds=1000)
    await worker.process(msg, {"run_id": str(run["id"]), "tenant_id": str(run["tenant_id"])})
    assert repo.finish.call_args.args[2] == "DEADLINE_EXCEEDED"


async def test_failed_commit_leaves_message_recoverable(context):
    worker, repo, redis, run, msg = context
    repo.finish.side_effect = ConnectionError("database stopped")
    with pytest.raises(ConnectionError):
        await worker.process(msg, {"run_id": str(run["id"]), "tenant_id": str(run["tenant_id"])})
    assert (await redis.xpending(STREAM, GROUP))["pending"] == 1


async def test_invalid_queue_resource_is_not_executed(context):
    worker, repo, redis, run, msg = context
    await worker.process(msg, {"run_id": "not-a-uuid", "tenant_id": str(run["tenant_id"])})
    repo.claim.assert_not_awaited()
    assert (await redis.xpending(STREAM, GROUP))["pending"] == 0


async def test_recovery_does_not_ack_a_live_lease(context):
    worker, repo, redis, run, msg = context
    repo.claim.return_value = None
    repo.terminal.return_value = False
    await worker.process(msg, {"run_id": str(run["id"]), "tenant_id": str(run["tenant_id"])})
    assert (await redis.xpending(STREAM, GROUP))["pending"] == 1
