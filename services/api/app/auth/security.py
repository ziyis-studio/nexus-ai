import asyncio
from dataclasses import dataclass
from uuid import UUID

import httpx
import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.errors import AppError
from app.schemas.models import Principal

bearer = HTTPBearer(auto_error=False)
_jwks: dict[str, jwt.PyJWKClient] = {}


async def verify_token(token: str, request: Request | None = None) -> Principal:
    settings = get_settings()
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") not in settings.jwt_algorithms:
            raise jwt.InvalidAlgorithmError()
        if header["alg"] == "HS256":
            if not settings.jwt_secret:
                raise jwt.InvalidKeyError()
            key = settings.jwt_secret
        else:
            url = settings.auth_url + "/.well-known/jwks.json"
            if url not in _jwks:
                _jwks[url] = jwt.PyJWKClient(url, cache_jwk_set=True, lifespan=300, timeout=5)
            key = (await asyncio.to_thread(_jwks[url].get_signing_key_from_jwt, token)).key
        claims = jwt.decode(
            token,
            key,
            algorithms=settings.jwt_algorithms,
            issuer=settings.issuer,
            audience=settings.jwt_audience,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
        principal = Principal(id=UUID(claims["sub"]), email=claims.get("email"))
    except (jwt.InvalidTokenError, jwt.PyJWKClientError, ValueError, KeyError) as exc:
        raise AppError(401, "INVALID_TOKEN", "Sign in again to continue.") from exc
    if settings.verify_session:
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                headers = {
                    "apikey": settings.supabase_publishable_key,
                    "Authorization": f"Bearer {token}",
                }
                response = await client.get(settings.auth_url + "/user", headers=headers)
                if response.status_code in (401, 403):
                    raise AppError(401, "INVALID_SESSION", "Your session has ended. Sign in again.")
                response.raise_for_status()
                active = await client.post(
                    settings.rest_url + "/rpc/session_active", headers=headers, json={}
                )
                active.raise_for_status()
                if not active.json():
                    raise AppError(401, "INVALID_SESSION", "Your session has ended. Sign in again.")
        except httpx.HTTPError as exc:
            raise AppError(
                503, "AUTH_UNAVAILABLE", "Authentication is temporarily unavailable."
            ) from exc
    return principal


@dataclass
class Identity:
    principal: Principal
    token: str


async def identity(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Identity:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise AppError(401, "AUTH_REQUIRED", "Sign in to continue.")
    return Identity(await verify_token(credentials.credentials), credentials.credentials)
