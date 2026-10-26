"""Launch services against the explicitly synthetic portable QA harness."""

import json
import os
import subprocess
import sys
from pathlib import Path

secret = json.loads(Path(".local/sandbox.json").read_text())["secret"]
env = {
    **os.environ,
    "ENVIRONMENT": "test",
    "SUPABASE_URL": "http://127.0.0.1:54321",
    "SUPABASE_REST_URL": "http://127.0.0.1:53000",
    "SUPABASE_PUBLISHABLE_KEY": "sandbox-public-key",
    "JWT_SECRET": secret,
    "JWT_ALGORITHMS": '["HS256"]',
    "DATABASE_URL": os.getenv(
        "SANDBOX_DATABASE_URL", "postgresql://postgres:nexus-local-only@127.0.0.1:55432/postgres"
    ),
    "REDIS_URL": os.getenv("SANDBOX_REDIS_URL", "redis://127.0.0.1:56379/0"),
    "LLM_PROVIDER": "fixture",
    "LLM_MODEL": "fixture",
    "PYTHONPATH": str(Path("services/api").resolve()) + os.pathsep + str(Path.cwd()),
    "PGRST_DB_URI": "postgresql://authenticator:nexus-local-only@127.0.0.1:55432/postgres",
    "PGRST_DB_SCHEMAS": "public",
    "PGRST_DB_ANON_ROLE": "anon",
    "PGRST_JWT_SECRET": secret,
    "PGRST_JWT_AUD": "authenticated",
    "PGRST_SERVER_HOST": "127.0.0.1",
    "PGRST_SERVER_PORT": "53000",
}
binary = (
    next(Path(".local/postgrest").glob("**/postgrest.exe"), None)
    if os.name == "nt"
    else Path(".local/postgrest/postgrest")
)
skip_postgrest = "--skip-postgrest" in sys.argv
if not skip_postgrest and (not binary or not binary.exists()):
    raise SystemExit(
        "Install the official PostgREST release into .local/postgrest first. See docs/TEST_PLAN.md."
    )
children = []
if os.name == "nt":
    env["PATH"] = (
        str(Path("node_modules/@embedded-postgres/windows-x64/native/bin").resolve())
        + os.pathsep
        + env["PATH"]
    )
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
    if not skip_postgrest:
        commands.insert(0, [str(binary.resolve())])
    for cmd in commands:
        children.append(subprocess.Popen(cmd, env=env))
    print(
        "QA services started. Auth and LLM are synthetic; PostgreSQL and PostgREST are real.",
        flush=True,
    )
    children[0 if skip_postgrest else 1].wait()
finally:
    for child in children:
        child.terminate()
    for child in children:
        child.wait(timeout=10)
