import asyncio
import contextlib
import json
import time
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from redis.exceptions import RedisError

from app.auth.security import verify_token
from app.core.config import get_settings
from app.core.errors import AppError
from app.repositories.data import RUN_FIELDS, Repository

router = APIRouter()


@router.websocket("/ws/v1/tenants/{tid}/runs/{run_id}")
async def subscribe(socket: WebSocket, tid: UUID, run_id: UUID):
    settings = get_settings()
    if socket.headers.get("origin") not in settings.cors_origins:
        await socket.close(code=4403)
        return
    await socket.accept()
    repo = None
    subscription = None
    try:
        message = await asyncio.wait_for(socket.receive_json(), timeout=5)
        if (
            not isinstance(message, dict)
            or message.get("type") != "authenticate"
            or not isinstance(message.get("token"), str)
            or len(message["token"]) > 16000
        ):
            raise AppError(401, "AUTH_REQUIRED", "Authentication required.")
        token = message["token"]
        principal = await verify_token(token)
        repo = Repository(token)

        async def authorize():
            await verify_token(token)
            members = await repo.call(
                "GET",
                "memberships",
                {
                    "tenant_id": f"eq.{tid}",
                    "user_id": f"eq.{principal.id}",
                    "is_active": "eq.true",
                    "select": "role",
                },
            )
            if not members:
                raise AppError(403, "TENANT_ACCESS_DENIED", "Workspace access denied.")

        await authorize()
        current = await repo.one("analysis_runs", tid, run_id, RUN_FIELDS)
        try:
            subscription = socket.app.state.redis.pubsub()
            await subscription.subscribe(f"nexus:run:{tid}:{run_id}")
        except RedisError:
            subscription = None
        previous = None
        last_auth = time.monotonic()
        while True:
            if time.monotonic() - last_auth > 15:
                await authorize()
                last_auth = time.monotonic()
            # RLS is reevaluated on every poll; expiry/session checks recur above.
            current = await repo.one("analysis_runs", tid, run_id, RUN_FIELDS)
            if current["status"] != previous:
                event = {
                    "queued": "run.queued",
                    "processing": "run.started",
                    "succeeded": "run.completed",
                    "failed": "run.failed",
                }[current["status"]]
                await socket.send_json(
                    {
                        "event_id": str(uuid4()),
                        "tenant_id": str(tid),
                        "run_id": str(run_id),
                        "type": event,
                        "status": current["status"],
                        "timestamp": datetime.now(UTC).isoformat(),
                        "payload": {
                            "attempt_count": current["attempt_count"],
                            "error_code": current.get("error_code"),
                        },
                    }
                )
                previous = current["status"]
            if previous in ("succeeded", "failed"):
                await socket.close(code=1000)
                return
            if subscription:
                try:
                    notification = await subscription.get_message(
                        ignore_subscribe_messages=True, timeout=1
                    )
                    if notification:
                        data = json.loads(notification["data"])
                        if data.get("type") == "run.progress":
                            await authorize()
                            await socket.send_json(
                                {
                                    "event_id": str(uuid4()),
                                    "tenant_id": str(tid),
                                    "run_id": str(run_id),
                                    "type": "run.progress",
                                    "status": "processing",
                                    "timestamp": datetime.now(UTC).isoformat(),
                                    "payload": {"stage": data.get("stage", "analyzing")},
                                }
                            )
                except (RedisError, ValueError):
                    subscription = None
            await asyncio.sleep(0.75)
    except (TimeoutError, ValueError, KeyError):
        await socket.close(code=4401)
    except AppError as exc:
        await socket.close(code=4401 if exc.status == 401 else 4403)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        if subscription:
            with contextlib.suppress(RedisError):
                await subscription.aclose()
        if repo:
            await repo.close()
