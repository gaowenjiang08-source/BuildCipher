"""Celery task definitions for async job processing."""

from __future__ import annotations

from celery import Celery
from cipher_genius.utils.config import get_settings

settings = get_settings()

# Initialize Celery app
celery_app = Celery(
    "cipher_genius",
    broker=f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}",
    backend=f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}",
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3000,  # 50 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)


@celery_app.task(name="cipher_genius.tasks.generate_scheme_async")
def generate_scheme_async(requirement: str, llm_provider: str = "openai", **kwargs) -> dict:
    """Async task for scheme generation."""
    from cipher_genius.api.service import GenerationService
    from cipher_genius.api.schemas import GenerateRequest

    request = GenerateRequest(
        requirement=requirement,
        llm_provider=llm_provider,
        **kwargs,
    )
    service = GenerationService(llm_provider)
    result = service.generate(request)
    return result.model_dump(mode="json")


@celery_app.task(name="cipher_genius.tasks.execute_mas_async")
def execute_mas_async(requirement: str, llm_provider: str = "openai", **kwargs) -> dict:
    """Async task for MAS orchestration."""
    from cipher_genius.api.mas_service import MASOrchestrationService
    from cipher_genius.api.schemas import MASRequest

    request = MASRequest(
        requirement=requirement,
        llm_provider=llm_provider,
        **kwargs,
    )
    service = MASOrchestrationService(llm_provider)
    result = service.execute(request)
    return result.model_dump(mode="json")


@celery_app.task(name="cipher_genius.tasks.generate_report_async")
def generate_report_async(
    mas_result: dict,
    scenario: str = "default",
    include_code: bool = True,
    include_pdf: bool = False,
) -> dict:
    """Async task for report generation."""
    from cipher_genius.api.report_service import MASReportService

    service = MASReportService()
    result = service.generate_report(
        mas_result=mas_result,
        scenario=scenario,
        include_code=include_code,
        include_pdf=include_pdf,
    )
    return result.model_dump(mode="json")
