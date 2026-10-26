"""Provision synthetic tenants/accounts through authorized Supabase Admin APIs."""

import asyncio
import os
import sys
from uuid import UUID

import httpx
import psycopg
from dotenv import load_dotenv

load_dotenv()


async def main():
    url = os.environ["SUPABASE_URL"].rstrip("/")
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    password = os.environ["DEMO_PASSWORD"]
    if len(password) < 12:
        raise SystemExit("Set a unique DEMO_PASSWORD of at least 12 characters.")
    headers = {"apikey": key, "Authorization": "Bearer " + key}
    async with httpx.AsyncClient(base_url=url, headers=headers, timeout=20) as client:
        # Paginate rather than treating the first page as the complete directory.
        users = {}
        page = 1
        while True:
            response = await client.get(
                "/auth/v1/admin/users", params={"page": page, "per_page": 100}
            )
            response.raise_for_status()
            batch = response.json()["users"]
            users.update({u["email"]: u["id"] for u in batch})
            if len(batch) < 100:
                break
            page += 1
        for role in ("admin", "agent", "viewer"):
            email = role + "@nexus.test"
            if email not in users:
                response = await client.post(
                    "/auth/v1/admin/users",
                    json={"email": email, "password": password, "email_confirm": True},
                )
                response.raise_for_status()
                users[email] = response.json()["id"]
    async with await psycopg.AsyncConnection.connect(os.environ["DATABASE_URL"]) as db:
        for suffix, name, slug in [
            ("1", "Acme Corporation", "acme"),
            ("2", "Nova Technologies", "nova"),
        ]:
            tid = UUID("10000000-0000-4000-8000-" + suffix.zfill(12))
            await db.execute(
                "insert into public.tenants(id,name,slug) values(%s,%s,%s) on conflict(id) do nothing",
                (tid, name, slug),
            )
            for role in ("admin", "agent", "viewer"):
                # Demo admin belongs to both; agent/viewer demonstrate one-tenant access.
                if suffix == "2" and role != "admin":
                    continue
                await db.execute(
                    "insert into public.memberships(tenant_id,user_id,role) values(%s,%s,%s) on conflict(tenant_id,user_id) do nothing",
                    (tid, users[role + "@nexus.test"], role),
                )
            exists = await (
                await db.execute("select 1 from public.tickets where tenant_id=%s limit 1", (tid,))
            ).fetchone()
            if not exists:
                await db.execute(
                    "insert into public.tickets(tenant_id,subject,description,customer_name,created_by) values(%s,%s,%s,%s,%s)",
                    (
                        tid,
                        "Delivery delayed for five days"
                        if suffix == "1"
                        else "Private Nova ticket",
                        "My order has been delayed for five days. Please verify the delivery status."
                        if suffix == "1"
                        else "This message belongs only to Nova Technologies.",
                        "Demo Customer",
                        users["admin@nexus.test"],
                    ),
                )
                await db.execute(
                    "insert into public.knowledge_docs(tenant_id,title,content,document_type,created_by) values(%s,%s,%s,%s,%s)",
                    (
                        tid,
                        "Delivery support procedure",
                        "Collect the order reference and contact the logistics team. Do not guarantee a delivery date.",
                        "policy",
                        users["admin@nexus.test"],
                    ),
                )
    print("Provisioned two synthetic organizations and three demo roles. No credentials printed.")


if __name__ == "__main__":
    asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop if sys.platform == "win32" else None)
