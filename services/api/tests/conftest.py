import os

os.environ["ENVIRONMENT"] = "test"
os.environ["VERIFY_SESSION"] = "false"
os.environ["JWT_ALGORITHMS"] = '["HS256"]'
os.environ["JWT_SECRET"] = "synthetic-test-key-not-a-production-credential-12345"

import time
from uuid import uuid4

import jwt
import pytest
from app.core.config import get_settings
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    get_settings.cache_clear()
    with TestClient(app) as client:
        yield client


@pytest.fixture
def token():
    settings = get_settings()
    return jwt.encode(
        {
            "sub": str(uuid4()),
            "iss": settings.issuer,
            "aud": "authenticated",
            "iat": int(time.time()),
            "exp": int(time.time()) + 600,
            "email": "agent@nexus.test",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
