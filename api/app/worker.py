"""
CIOTX API — ARQ Worker
Background job processor for scan pipeline.
"""

from arq.connections import RedisSettings

from app.config import settings


class WorkerSettings:
    """ARQ Worker configuration."""
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    functions: list = []  # Scan functions registered in Phase 3
    max_jobs: int = 5
    job_timeout: int = 900  # 15 minutes
    keep_result: int = 3600  # 1 hour
    health_check_interval: int = 10
