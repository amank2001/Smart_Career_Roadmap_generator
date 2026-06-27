"""Event handlers that wire domain events to service actions.

This module registers handlers on the global event bus to react to domain events.
Handlers run within the context of the emitting request's database session, which
is passed through the event bus indirectly via a session factory.

Since event handlers need database access but run outside of FastAPI's dependency
injection, we use a session factory approach: handlers create their own sessions
for side effects triggered by events.
"""

from __future__ import annotations

import logging

from app.core.database import AsyncSessionLocal
from app.core.events import PlanCompleted, RoadmapCompleted, event_bus
from app.services.progress_service import ProgressService

logger = logging.getLogger(__name__)


@event_bus.subscribe(PlanCompleted)
async def handle_plan_completed(event: PlanCompleted) -> None:
    """Update skill proficiency levels when a plan is completed.

    Creates a new database session to perform the proficiency update,
    ensuring the side effect is committed independently.

    Requirements: 8.2, 8.3
    """
    logger.info(
        "Handling PlanCompleted event: user_id=%s, plan_id=%s",
        event.user_id,
        event.plan_id,
    )
    async with AsyncSessionLocal() as session:
        try:
            service = ProgressService(db=session)
            await service.update_skill_proficiency(
                user_id=event.user_id, plan_id=event.plan_id
            )
            await session.commit()
            logger.info(
                "Skill proficiency updated for user %s after plan %s completion",
                event.user_id,
                event.plan_id,
            )
        except Exception:
            await session.rollback()
            logger.exception(
                "Failed to update skill proficiency for user %s, plan %s",
                event.user_id,
                event.plan_id,
            )


@event_bus.subscribe(RoadmapCompleted)
async def handle_roadmap_completed(event: RoadmapCompleted) -> None:
    """Log roadmap completion event.

    In a full implementation, this could trigger notifications, achievement
    badges, or analytics updates. For now, it logs the milestone.

    Requirements: 8.3
    """
    logger.info(
        "Roadmap completed! user_id=%s, roadmap_id=%s",
        event.user_id,
        event.roadmap_id,
    )
