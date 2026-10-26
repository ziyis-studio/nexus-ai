import asyncio
import contextlib
import json
import logging
import random
import signal
import socket
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from app.core.config import get_settings
from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError, ResponseError

from services.worker.ai import InvalidOutput, generate, transient
from services.worker.repository import WorkerRepository

logger = logging.getLogger("nexus.worker")
STREAM, GROUP = "nexus:jobs", "nexus-workers"


class Worker:
    def __init__(self, settings, repository=None, redis=None):
        self.settings = settings
        self.repo = repository or WorkerRepository(settings)
        self.redis = redis or Redis.from_url(
            settings.redis_url, decode_responses=True, socket_connect_timeout=3, socket_timeout=6
        )
        self.stop = asyncio.Event()
        self.consumer = socket.gethostname() + ":" + str(uuid4())[:8]

    async def progress(self, run, stage):
        with contextlib.suppress(RedisError):
            await self.redis.publish(
                f"nexus:run:{run['tenant_id']}:{run['id']}",
                json.dumps({"type": "run.progress", "stage": stage}),
            )

    async def process(self, message_id, payload):
        try:
            tid, run_id = UUID(payload["tenant_id"]), UUID(payload["run_id"])
        except (ValueError, KeyError, TypeError):
            await self.acknowledge(message_id)
            return
        run = await self.repo.claim(tid, run_id)
        if run is None:
            if await self.repo.terminal(tid, run_id):
                await self.acknowledge(message_id)
            return
        started = time.monotonic()
        code, output = None, None
        try:
            # The persistent started_at is the overall deadline across crashes.
            age = (datetime.now(UTC) - run["started_at"]).total_seconds()
            if age >= self.settings.job_deadline:
                raise TimeoutError()
            if run["model_id"] != self.settings.llm_model:
                raise InvalidOutput("Model differs from the configured allowlist")
            async with asyncio.timeout(max(0.01, self.settings.job_deadline - age)):
                if not await self.repo.allowed(run):
                    raise PermissionError()
                await self.progress(run, "retrieving")
                documents = await self.repo.documents(tid, run["ticket_snapshot"])
                while run["attempt_count"] < self.settings.max_attempts:
                    attempt = await self.repo.attempt(run)
                    if not attempt:
                        return
                    run["attempt_count"] = attempt["attempt_count"]
                    await self.progress(run, "analyzing")
                    try:
                        async with asyncio.timeout(self.settings.llm_timeout):
                            output = await generate(
                                self.settings, run["ticket_snapshot"], documents, run["model_id"]
                            )
                        break
                    except Exception as exc:
                        if not transient(exc) and not isinstance(exc, TimeoutError):
                            raise
                        if run["attempt_count"] >= self.settings.max_attempts:
                            raise
                        await self.progress(run, "retrying")
                        await asyncio.sleep(
                            2 ** (run["attempt_count"] - 1) + random.uniform(0, 0.5)
                        )
                if output is None:
                    code = "RETRY_EXHAUSTED"
                if not await self.repo.allowed(run):
                    raise PermissionError()
        except TimeoutError:
            code = "DEADLINE_EXCEEDED"
        except PermissionError:
            code = "AUTHORIZATION_REVOKED"
        except (InvalidOutput, ValidationError, ValueError):
            code = "INVALID_AI_OUTPUT"
        except Exception as exc:
            code = "PROVIDER_UNAVAILABLE" if transient(exc) else "PROCESSING_ERROR"
        if code:
            output = None
        # If the DB transaction fails, leave the message pending for lease recovery.
        committed = await self.repo.finish(run, output, code)
        if committed or await self.repo.terminal(tid, run_id):
            await self.acknowledge(message_id)
        logger.info(
            json.dumps(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "severity": "INFO",
                    "service": "worker",
                    "event": "job.completed" if output else "job.failed",
                    "tenant_id": str(tid),
                    "run_id": str(run_id),
                    "duration_ms": round((time.monotonic() - started) * 1000, 2),
                    "attempt_count": run["attempt_count"],
                    "error_code": code,
                }
            )
        )

    async def acknowledge(self, message_id):
        await self.redis.xack(STREAM, GROUP, message_id)
        await self.redis.xdel(STREAM, message_id)

    async def consume(self, index):
        consumer = f"{self.consumer}:{index}"
        recovery_cursor = "0-0"
        while not self.stop.is_set():
            try:
                recovered = await self.redis.xautoclaim(
                    STREAM,
                    GROUP,
                    consumer,
                    self.settings.lease_seconds * 1000,
                    recovery_cursor,
                    count=1,
                )
                recovery_cursor = recovered[0] if recovered else "0-0"
                messages = recovered[1] if recovered else []
                if not messages:
                    batches = await self.redis.xreadgroup(
                        GROUP, consumer, {STREAM: ">"}, count=1, block=2000
                    )
                    messages = batches[0][1] if batches else []
                for message_id, payload in messages:
                    await self.process(message_id, payload)
            except Exception as exc:
                logger.warning(
                    json.dumps(
                        {
                            "timestamp": datetime.now(UTC).isoformat(),
                            "severity": "WARNING",
                            "service": "worker",
                            "event": "worker.recoverable_error",
                            "error_code": type(exc).__name__,
                        }
                    )
                )
                await asyncio.sleep(2)

    async def reconcile(self):
        while not self.stop.is_set():
            try:
                for row in await self.repo.pending():
                    # NX bounds redelivery growth; DB lease is the execution lock.
                    if await self.redis.set(f"nexus:reconcile:{row['id']}", "1", ex=15, nx=True):
                        await self.redis.xadd(
                            STREAM, {"tenant_id": str(row["tenant_id"]), "run_id": str(row["id"])}
                        )
                depth = await self.redis.xlen(STREAM)
                Path(tempfile.gettempdir(), "nexus-worker-heartbeat").touch()
                logger.info(
                    json.dumps(
                        {
                            "timestamp": datetime.now(UTC).isoformat(),
                            "severity": "INFO",
                            "service": "worker",
                            "event": "queue.sample",
                            "queue_depth": depth,
                        }
                    )
                )
            except Exception as exc:
                logger.warning(
                    json.dumps(
                        {
                            "timestamp": datetime.now(UTC).isoformat(),
                            "severity": "WARNING",
                            "service": "worker",
                            "event": "reconcile.retry",
                            "error_code": type(exc).__name__,
                        }
                    )
                )
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self.stop.wait(), 10)

    async def run(self):
        await self.repo.open()
        try:
            try:
                await self.redis.xgroup_create(STREAM, GROUP, id="0", mkstream=True)
            except ResponseError as exc:
                if "BUSYGROUP" not in str(exc):
                    raise
            await asyncio.gather(
                self.reconcile(),
                *(self.consume(i) for i in range(self.settings.worker_concurrency)),
            )
        finally:
            await self.repo.close()
            await self.redis.aclose()


async def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    worker = Worker(get_settings())
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, worker.stop.set)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop if sys.platform == "win32" else None)
