"""Task management package."""

from __future__ import annotations

from cipher_genius.tasks.celery_tasks import celery_app

__all__ = ["celery_app"]
