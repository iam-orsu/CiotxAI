"""
CIOTX API — ARQ Worker
Background job processor for scan pipeline.
"""

import asyncio

from arq import create_pool
from arq.connections import RedisSettings

from app.config import settings


async def run_scan_job(ctx: dict, scan_id: str, project_id: str, repo_url: str | None = None):
    """
    ARQ job: Run the full scan pipeline.
    Picked up by worker containers. Survives server restarts.
    """
    from app.services.scanner import run_scan
    await run_scan(scan_id, project_id, repo_url)


async def enqueue_scan(scan_id: str, project_id: str, repo_url: str | None = None):
    """Enqueue a scan job to Redis. Called from API route."""
    redis = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    await redis.enqueue_job("run_scan_job", scan_id, project_id, repo_url)
    await redis.close()


class WorkerSettings:
    """ARQ Worker configuration."""
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    functions: list = [run_scan_job]
    max_jobs: int = 5
    job_timeout: int = 900  # 15 minutes
    keep_result: int = 3600  # 1 hour
    health_check_interval: int = 10
