"""Synthetic login adapter for portable QA only. Never deploy this module."""

import json
import os
import secrets
import threading
import time
from pathlib import Path
from uuid import uuid4

import fakeredis
import jwt
import psycopg
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

path = Path(".local/sandbox.json")
if not path.exists():
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({"secret": secrets.token_urlsafe(48)}), encoding="utf-8")
key = json.loads(path.read_text())["secret"]
DB = os.getenv(
    "SANDBOX_DATABASE_URL", "postgresql://postgres:nexus-local-only@127.0.0.1:55432/postgres"
)
ISSUER = "http://127.0.0.1:54321/auth/v1"
app = FastAPI(docs_url=None, openapi_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
USERS = {
    "admin@nexus.test": "20000000-0000-4000-8000-000000000001",
    "agent@nexus.test": "20000000-0000-4000-8000-000000000002",
    "viewer@nexus.test": "20000000-0000-4000-8000-000000000003",
}


def decode(token):
    return jwt.decode(token, key, algorithms=["HS256"], issuer=ISSUER, audience="authenticated")


def user(uid, email):
    return {
        "id": uid,
        "email": email,
        "aud": "authenticated",
        "role": "authenticated",
        "app_metadata": {},
        "user_metadata": {},
        "created_at": "2026-10-27T00:00:00Z",
    }


@app.post("/auth/v1/token")
async def login(request: Request):
    body = await request.json()
    if request.query_params.get("grant_type") == "refresh_token":
        try:
            claims = decode(body["refresh_token"])
            email = claims["email"]
        except Exception:
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_grant", "error_description": "Session expired"},
            )
    else:
        email = body.get("email", "")
        if email not in USERS or body.get("password") != "Nexus-demo-2026!":
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_grant", "error_description": "Invalid credentials"},
            )
    uid = USERS[email]
    sid = str(uuid4())
    now = int(time.time())
    with psycopg.connect(DB) as db:
        db.execute("insert into auth.sessions(id,user_id) values(%s,%s)", (sid, uid))
    token = jwt.encode(
        {
            "sub": uid,
            "email": email,
            "role": "authenticated",
            "aud": "authenticated",
            "iss": ISSUER,
            "iat": now,
            "exp": now + 3600,
            "session_id": sid,
        },
        key,
        algorithm="HS256",
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": 3600,
        "expires_at": now + 3600,
        "refresh_token": token,
        "user": user(uid, email),
    }


@app.get("/auth/v1/user")
async def current(request: Request):
    try:
        claims = decode(request.headers.get("authorization", "").removeprefix("Bearer "))
        with psycopg.connect(DB) as db:
            active = db.execute(
                "select 1 from auth.sessions where id=%s and user_id=%s",
                (claims["session_id"], claims["sub"]),
            ).fetchone()
        if not active:
            raise ValueError()
        return user(claims["sub"], claims["email"])
    except Exception:
        return JSONResponse(status_code=401, content={"error": "invalid_token"})


@app.post("/auth/v1/logout")
async def logout(request: Request):
    try:
        claims = decode(request.headers.get("authorization", "").removeprefix("Bearer "))
        with psycopg.connect(DB) as db:
            db.execute("delete from auth.sessions where id=%s", (claims["session_id"],))
    except Exception:
        pass
    return {}


if __name__ == "__main__":
    # Fakeredis is a test double. Real Redis is exercised by CI service containers.
    if os.getenv("SANDBOX_FAKE_REDIS", "true") == "true":
        server = fakeredis.TcpFakeServer(("127.0.0.1", 56379), server_type="redis")
        threading.Thread(target=server.serve_forever, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=54321, access_log=False)
