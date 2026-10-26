"""Run actual local Supabase Auth/Data API with a fixture LLM for integration QA."""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

from seed import main as provision

status = json.loads(Path(".local/supabase-status.json").read_text())
public_key = status.get("PUBLISHABLE_KEY") or status["ANON_KEY"]
os.environ.update(
    {
        "ENVIRONMENT": "test",
        "SUPABASE_URL": status["API_URL"],
        "SUPABASE_PUBLISHABLE_KEY": public_key,
        "SUPABASE_SERVICE_ROLE_KEY": status["SERVICE_ROLE_KEY"],
        "JWT_ISSUER": status["API_URL"].rstrip("/") + "/auth/v1",
        "JWT_SECRET": status["JWT_SECRET"],
        "JWT_ALGORITHMS": '["HS256","ES256","RS256"]',
        "DATABASE_URL": status["DB_URL"],
        "REDIS_URL": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
        "LLM_PROVIDER": "fixture",
        "LLM_MODEL": "fixture",
        "VERIFY_SESSION": "true",
        "DEMO_PASSWORD": os.environ.get("E2E_PASSWORD", "Nexus-demo-2026!"),
        "PYTHONPATH": str(Path("services/api").resolve()) + os.pathsep + str(Path.cwd()),
        "NUXT_PUBLIC_API_BASE": "http://127.0.0.1:8000",
        "NUXT_PUBLIC_SUPABASE_URL": status["API_URL"],
        "NUXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY": public_key,
    }
)
asyncio.run(
    provision(), loop_factory=asyncio.SelectorEventLoop if sys.platform == "win32" else None
)
children = []
try:
    commands = [
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--no-access-log",
        ],
        [sys.executable, "-m", "services.worker.main"],
    ]
    if "--web" in sys.argv:
        commands.append(
            [
                os.environ.get("NODE_BINARY", "node"),
                "node_modules/nuxt/bin/nuxt.mjs",
                "dev",
                "apps/web",
                "--host",
                "127.0.0.1",
            ]
        )
    for command in commands:
        children.append(subprocess.Popen(command, env=os.environ.copy()))
    print(
        "Real local Supabase services started; the LLM is an explicit deterministic fixture.",
        flush=True,
    )
    children[0].wait()
finally:
    for child in children:
        child.terminate()
    for child in children:
        child.wait(timeout=10)
