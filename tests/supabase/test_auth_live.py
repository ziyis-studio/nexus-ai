import json
import os
import time
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("NEXUS_REAL_SUPABASE") != "1", reason="Requires the real local Supabase stack."
)


def test_real_supabase_auth_ticket_analysis_review_and_session_revocation():
    status = json.loads(Path(".local/supabase-status.json").read_text())
    key = status.get("PUBLISHABLE_KEY") or status["ANON_KEY"]
    with httpx.Client(timeout=15) as client:
        login = client.post(
            status["API_URL"] + "/auth/v1/token?grant_type=password",
            json={
                "email": "admin@nexus.test",
                "password": os.getenv("E2E_PASSWORD", "Nexus-demo-2026!"),
            },
            headers={"apikey": key},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": "Bearer " + token}
        api = "http://127.0.0.1:8000/api/v1"
        tenants = client.get(api + "/me/tenants", headers=headers)
        assert tenants.status_code == 200 and len(tenants.json()) == 2
        tid = next(row["id"] for row in tenants.json() if row["slug"] == "acme")
        ticket = client.post(
            f"{api}/tenants/{tid}/tickets",
            json={
                "subject": "Real Supabase delivery test",
                "description": "My order has been delayed for five days. Please verify the status.",
            },
            headers=headers,
        )
        assert ticket.status_code == 201
        run = client.post(
            f"{api}/tenants/{tid}/tickets/{ticket.json()['id']}/analyze",
            headers={**headers, "Idempotency-Key": str(uuid4())},
        )
        assert run.status_code == 202
        run_id = run.json()["run_id"]
        for _ in range(40):
            current = client.get(f"{api}/tenants/{tid}/runs/{run_id}", headers=headers)
            if current.json()["status"] in ("succeeded", "failed"):
                break
            time.sleep(0.5)
        assert current.json()["status"] == "succeeded", current.text
        result = client.get(f"{api}/tenants/{tid}/runs/{run_id}/result", headers=headers)
        assert result.status_code == 200 and result.json()["source_document_ids"]
        review = client.post(f"{api}/tenants/{tid}/runs/{run_id}/approve", headers=headers)
        assert review.status_code == 200 and review.json()["review_status"] == "approved"
        logout = client.post(
            status["API_URL"] + "/auth/v1/logout?scope=global", headers={**headers, "apikey": key}
        )
        assert logout.status_code in (200, 204)
        assert client.get(api + "/me", headers=headers).status_code == 401
