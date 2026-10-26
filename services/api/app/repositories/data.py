import base64
import json
from datetime import datetime
from uuid import UUID

import httpx

from app.core.config import get_settings
from app.core.errors import AppError, not_found

TICKET_FIELDS = "id,tenant_id,subject,description,status,priority,customer_name,customer_email,external_reference,created_by,created_at,updated_at"
DOC_FIELDS = "id,tenant_id,title,content,document_type,is_active,created_by,created_at,updated_at"
RUN_FIELDS = "id,tenant_id,ticket_id,initiated_by,status,model_id,attempt_count,error_code,error_message,created_at,started_at,completed_at"


class Repository:
    def __init__(self, token: str):
        settings = get_settings()
        self.client = httpx.AsyncClient(
            base_url=settings.rest_url + "/",
            timeout=10,
            headers={
                "apikey": settings.supabase_publishable_key,
                "Authorization": f"Bearer {token}",
                "Prefer": "return=representation",
            },
        )

    async def close(self):
        await self.client.aclose()

    async def call(self, method: str, path: str, params=None, body=None):
        try:
            response = await self.client.request(method, path, params=params, json=body)
        except httpx.HTTPError as exc:
            raise AppError(
                503, "DATABASE_UNAVAILABLE", "The data service is temporarily unavailable."
            ) from exc
        if response.is_error:
            try:
                error = response.json()
            except ValueError:
                error = {}
            code, message = error.get("code"), error.get("message", "")
            if code in ("42501", "PGRST301", "PGRST302"):
                raise AppError(
                    403, "TENANT_ACCESS_DENIED", "You do not have permission for this action."
                )
            if code == "P0002":
                raise not_found()
            if code == "23505":
                raise AppError(
                    409,
                    "REVIEW_FINAL" if "REVIEW_FINAL" in message else "IDEMPOTENCY_CONFLICT",
                    "The request conflicts with an existing operation.",
                )
            if code in ("23514", "22P02"):
                raise AppError(400, "INVALID_TRANSITION", "This change is not allowed.")
            if "USAGE_LIMIT" in message:
                raise AppError(429, "USAGE_LIMIT", "Workspace AI limit reached. Try again later.")
            raise AppError(
                503, "DATABASE_UNAVAILABLE", "The data service could not complete the request."
            )
        return response.json() if response.content else None

    async def one(self, table, tid, record_id, fields="*", key="id"):
        rows = await self.call(
            "GET",
            table,
            {"tenant_id": f"eq.{tid}", key: f"eq.{record_id}", "select": fields, "limit": 1},
        )
        if not rows:
            raise not_found()
        return rows[0]

    async def page(self, table, tid, limit, cursor, fields="*", filters=None):
        params = {
            "tenant_id": f"eq.{tid}",
            "select": fields,
            "order": "created_at.desc,id.desc",
            "limit": limit + 1,
            **(filters or {}),
        }
        if cursor:
            try:
                value = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
                if value["tenant"] != str(tid):
                    raise ValueError()
                timestamp = datetime.fromisoformat(value["at"])
                if not timestamp.tzinfo:
                    raise ValueError()
                at, uid = timestamp.isoformat(), UUID(value["id"])
                params["or"] = f"(created_at.lt.{at},and(created_at.eq.{at},id.lt.{uid}))"
            except (ValueError, TypeError, KeyError) as exc:
                raise AppError(
                    400, "INVALID_CURSOR", "This pagination cursor is invalid for the workspace."
                ) from exc
        rows = await self.call("GET", table, params)
        next_cursor = None
        if len(rows) > limit:
            last = rows[limit - 1]
            next_cursor = (
                base64.urlsafe_b64encode(
                    json.dumps(
                        {"tenant": str(tid), "at": last["created_at"], "id": last["id"]}
                    ).encode()
                )
                .decode()
                .rstrip("=")
            )
        return {"items": rows[:limit], "next_cursor": next_cursor}


def search_filter(query: str) -> str:
    return (
        "ilike.*"
        + query.replace("\\", "\\\\").replace("*", "\\*").replace("%", "\\%").replace("_", "\\_")
        + "*"
    )
