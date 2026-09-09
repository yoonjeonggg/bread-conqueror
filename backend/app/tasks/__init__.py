"""Background jobs (APScheduler). Wire into the FastAPI lifespan when needed.

Planned jobs:
- rebuild_rankings: rehydrate Redis ZSETs from user_stats (source of truth)
- recalc_tiers: nightly tier reconciliation
- expire_verification_codes: cleanup

Kept as a stub for phase 1; see app/services/ranking_service.py.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()


def start() -> None:  # pragma: no cover - infra glue
    if not scheduler.running:
        scheduler.start()
