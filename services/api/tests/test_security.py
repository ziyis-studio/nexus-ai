import time
from uuid import uuid4

import jwt
import pytest
import respx
from app.auth.security import verify_token
from app.core.config import get_settings
from app.core.errors import AppError
from httpx import Response

TID, OTHER, UID = str(uuid4()), str(uuid4()), str(uuid4())


def test_unauthenticated(client):
    response = client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"
    assert response.headers["x-request-id"]


@pytest.mark.parametrize(
    "kind", ["expired", "signature", "issuer", "audience", "algorithm", "subject", "missing_exp"]
)
def test_invalid_tokens(client, kind):
    settings = get_settings()
    claims = {
        "sub": str(uuid4()),
        "iss": settings.issuer,
        "aud": "authenticated",
        "iat": int(time.time()) - 120,
        "exp": int(time.time()) + 30,
    }
    secret, algorithm = settings.jwt_secret, "HS256"
    if kind == "expired":
        claims["exp"] = int(time.time()) - 5
    if kind == "signature":
        secret = "incorrect-key-which-is-long-enough-for-tests"
    if kind == "issuer":
        claims["iss"] = "https://wrong.test/auth/v1"
    if kind == "audience":
        claims["aud"] = "wrong"
    if kind == "algorithm":
        algorithm = "HS384"
    if kind == "subject":
        claims["sub"] = "not-a-uuid"
    if kind == "missing_exp":
        del claims["exp"]
    token = jwt.encode(claims, secret, algorithm=algorithm)
    response = client.get("/api/v1/me", headers={"Authorization": "Bearer " + token})
    assert response.status_code == 401
    assert "incorrect-key" not in response.text


@respx.mock
def test_tenant_membership_required(client, token):
    respx.get(get_settings().rest_url + "/memberships").mock(return_value=Response(200, json=[]))
    response = client.get(
        f"/api/v1/tenants/{TID}/tickets", headers={"Authorization": "Bearer " + token}
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("POST", "tickets", {"subject": "Testing", "description": "This is a support request."}),
        ("POST", f"tickets/{UID}/analyze", None),
        ("PATCH", f"tickets/{UID}", {"status": "resolved"}),
        ("POST", f"runs/{UID}/approve", None),
        ("POST", f"runs/{UID}/reject", None),
        (
            "POST",
            "knowledge",
            {"title": "A valid document", "content": "A valid policy for testing."},
        ),
        ("GET", "members", None),
        ("GET", "audit", None),
    ],
)
@respx.mock
def test_viewer_denied_privileged_actions(client, token, method, path, body):
    respx.get(get_settings().rest_url + "/memberships").mock(
        return_value=Response(200, json=[{"role": "viewer"}])
    )
    response = client.request(
        method,
        f"/api/v1/tenants/{TID}/{path}",
        json=body,
        headers={"Authorization": "Bearer " + token},
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "table,path",
    [
        ("tickets", f"tickets/{UID}"),
        ("knowledge_docs", f"knowledge/{UID}"),
        ("analysis_runs", f"runs/{UID}"),
        ("ai_results", f"runs/{UID}/result"),
    ],
)
@respx.mock
def test_foreign_resource_not_found(client, token, table, path):
    respx.get(get_settings().rest_url + "/memberships").mock(
        return_value=Response(200, json=[{"role": "agent"}])
    )
    route = respx.get(get_settings().rest_url + "/" + table).mock(
        return_value=Response(200, json=[])
    )
    response = client.get(
        f"/api/v1/tenants/{TID}/{path}", headers={"Authorization": "Bearer " + token}
    )
    assert response.status_code == 404
    assert route.calls.last.request.url.params["tenant_id"] == f"eq.{TID}"


@respx.mock
def test_body_cannot_spoof_tenant_or_user(client, token):
    respx.get(get_settings().rest_url + "/memberships").mock(
        return_value=Response(200, json=[{"role": "agent"}])
    )
    response = client.post(
        f"/api/v1/tenants/{TID}/tickets",
        json={
            "tenant_id": OTHER,
            "created_by": UID,
            "subject": "Spoofing request",
            "description": "This request must be rejected.",
        },
        headers={"Authorization": "Bearer " + token},
    )
    assert response.status_code == 422
    assert OTHER not in response.text


def test_websocket_requires_allowed_origin(client):
    from starlette.websockets import WebSocketDisconnect

    with (
        pytest.raises(WebSocketDisconnect) as error,
        client.websocket_connect(f"/ws/v1/tenants/{TID}/runs/{UID}"),
    ):
        pass
    assert error.value.code == 4403


def test_websocket_invalid_token(client):
    from starlette.websockets import WebSocketDisconnect

    with client.websocket_connect(
        f"/ws/v1/tenants/{TID}/runs/{UID}", headers={"origin": "http://127.0.0.1:3000"}
    ) as socket:
        socket.send_json({"type": "authenticate", "token": "invalid"})
        with pytest.raises(WebSocketDisconnect) as error:
            socket.receive_json()
        assert error.value.code == 4401


@respx.mock
def test_websocket_cross_tenant(client, token):
    from starlette.websockets import WebSocketDisconnect

    respx.get(get_settings().rest_url + "/memberships").mock(return_value=Response(200, json=[]))
    with client.websocket_connect(
        f"/ws/v1/tenants/{OTHER}/runs/{UID}", headers={"origin": "http://127.0.0.1:3000"}
    ) as socket:
        socket.send_json({"type": "authenticate", "token": token})
        with pytest.raises(WebSocketDisconnect) as error:
            socket.receive_json()
        assert error.value.code == 4403


@respx.mock
async def test_revoked_session_is_rejected(monkeypatch, token):
    monkeypatch.setenv("VERIFY_SESSION", "true")
    get_settings.cache_clear()
    respx.get(get_settings().auth_url + "/user").mock(return_value=Response(200, json={"id": UID}))
    respx.post(get_settings().rest_url + "/rpc/session_active").mock(
        return_value=Response(200, json=False)
    )
    with pytest.raises(AppError) as error:
        await verify_token(token)
    assert error.value.status == 401
    get_settings.cache_clear()
