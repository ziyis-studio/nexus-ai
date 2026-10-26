import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import uuid4

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from starlette.exceptions import HTTPException

from app.core.config import get_settings
from app.core.errors import AppError
from app.routers import api, realtime
from app.schemas.models import ErrorResponse

logger = logging.getLogger("nexus.api")
logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(application: FastAPI):
    settings = get_settings()
    application.state.redis = Redis.from_url(
        settings.redis_url, decode_responses=True, socket_connect_timeout=3, socket_timeout=3
    )
    yield
    await application.state.redis.aclose()


app = FastAPI(
    title="NEXUS AI",
    version="1.0.0",
    description="Tenant-isolated ticket intelligence API. Business writes flow through this API; all AI replies require human review.",
    lifespan=lifespan,
    responses={
        code: {"model": ErrorResponse} for code in (400, 401, 403, 404, 409, 422, 429, 500, 503)
    },
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = str(uuid4())
    started = time.monotonic()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    route = request.scope.get("route")
    logger.info(
        json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "severity": "INFO",
                "service": "api",
                "request_id": request.state.request_id,
                "event": "http.request",
                "route": getattr(route, "path", "unmatched"),
                "status": response.status_code,
                "latency_ms": round((time.monotonic() - started) * 1000, 2),
            }
        )
    )
    return response


def error_response(request, status, code, message):
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": getattr(request.state, "request_id", str(uuid4())),
            }
        },
    )


@app.exception_handler(AppError)
async def app_error(request: Request, exc: AppError):
    return error_response(request, exc.status, exc.code, exc.message)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return error_response(
        request, 422, "VALIDATION_ERROR", "Check the request fields and try again."
    )


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return error_response(
        request, exc.status_code, "HTTP_ERROR", "This request could not be completed."
    )


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.error(
        json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "severity": "ERROR",
                "service": "api",
                "request_id": getattr(request.state, "request_id", None),
                "event": "http.error",
                "error_code": type(exc).__name__,
            }
        )
    )
    return error_response(
        request,
        500,
        "INTERNAL_ERROR",
        "An unexpected error occurred. Use the request ID when contacting support.",
    )


@app.get("/health/live", tags=["Operations"])
async def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["Operations"])
async def ready(request: Request) -> dict[str, str]:
    try:
        await request.app.state.redis.ping()
        async with httpx.AsyncClient(timeout=4) as client:
            response = await client.get(
                get_settings().rest_url + "/",
                headers={"apikey": get_settings().supabase_publishable_key},
            )
            response.raise_for_status()
    except Exception as exc:
        raise AppError(
            503, "DEPENDENCY_UNAVAILABLE", "One or more dependencies are unavailable."
        ) from exc
    return {"status": "ready"}


app.include_router(api.router)
app.include_router(realtime.router)
