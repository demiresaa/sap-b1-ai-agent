"""Celery app — Redis broker + result backend."""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "sap_b1_ai_agent",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.tasks",
        "app.workers.email_poller",
        "app.workers.graph_poller",
        "app.workers.sync_tasks",
    ],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
    timezone="Europe/Istanbul",
    beat_schedule={
        "poll-imap-inbox": {
            "task": "app.workers.email_poller.poll_inbox",
            "schedule": crontab(minute=f"*/{max(1, settings.email_poll_interval_seconds // 60)}"),
        },
        "sync-items-full-daily": {
            "task": "sync.items.full",
            "schedule": crontab(hour=2, minute=0),
        },
        "sync-items-incremental-hourly": {
            "task": "sync.items.incremental",
            "schedule": crontab(minute=30),
        },
        "sync-bp-full-daily": {
            "task": "sync.bp.full",
            "schedule": crontab(hour=2, minute=15),
        },
        "poll-graph-inbox": {
            "task": "app.workers.graph_poller.poll_graph_inbox",
            "schedule": crontab(
                minute=f"*/{max(1, settings.ms_graph_poll_interval_minutes)}"
            ),
        },
    },
)
