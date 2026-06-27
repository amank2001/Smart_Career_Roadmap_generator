"""Roadmap Generator Service — creates and manages personalised learning roadmaps."""

import math
import uuid
from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.provider import AIProvider, SkillGap as AISkillGap, RoadmapTopic as AIRoadmapTopic
from app.core.exceptions import InvalidWeeklyHoursError, NoGapAnalysisError
from app.models.roadmap import (
    LearningRoadmap as LearningRoadmapORM,
    LearningResource as LearningResourceORM,
    RoadmapTopic as RoadmapTopicORM,
)
from app.models.skill_gap import SkillGapAnalysis as SkillGapAnalysisORM
from app.schemas.roadmap import (
    LearningRoadmap,
    LearningResource,
    RoadmapTopic,
)


# Priority ordering for gap categories (lower index = higher priority)
_CATEGORY_PRIORITY = {"critical": 0, "important": 1, "nice-to-have": 2}


class RoadmapService:
    """Database-backed service for learning roadmap generation and management."""

    def __init__(self, db: AsyncSession, ai_provider: AIProvider) -> None:
        self._db = db
        self._ai_provider = ai_provider

    # ── Validation helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _validate_weekly_hours(weekly_hours: int) -> None:
        """Validate weekly study hours are within the allowed range (1-40)."""
        if weekly_hours < 1 or weekly_hours > 40:
            raise InvalidWeeklyHoursError()

    # ── Topological sort with priority ─────────────────────────────────────────

    @staticmethod
    def _topological_sort_with_priority(topics: list[AIRoadmapTopic]) -> list[AIRoadmapTopic]:
        """Order topics so prerequisites appear before dependents.

        At the same dependency level, prioritizes: critical > important > nice-to-have.
        Uses Kahn's algorithm with a priority-aware selection.
        """
        topic_map: dict[UUID, AIRoadmapTopic] = {t.id: t for t in topics}
        topic_ids = set(topic_map.keys())

        # Build adjacency list and in-degree count
        in_degree: dict[UUID, int] = {t.id: 0 for t in topics}
        dependents: dict[UUID, list[UUID]] = defaultdict(list)

        for topic in topics:
            for prereq_id in topic.prerequisites:
                # Only count prerequisites that are in our topic set
                if prereq_id in topic_ids:
                    in_degree[topic.id] += 1
                    dependents[prereq_id].append(topic.id)

        # Start with topics that have no prerequisites (in-degree 0)
        # Sort by category priority so critical topics come first
        ready: list[UUID] = [
            tid for tid, deg in in_degree.items() if deg == 0
        ]
        ready.sort(key=lambda tid: _CATEGORY_PRIORITY.get(topic_map[tid].category, 99))

        sorted_topics: list[AIRoadmapTopic] = []

        while ready:
            # Pick the highest-priority topic from the ready list
            current_id = ready.pop(0)
            sorted_topics.append(topic_map[current_id])

            # Reduce in-degree for dependents
            for dep_id in dependents[current_id]:
                in_degree[dep_id] -= 1
                if in_degree[dep_id] == 0:
                    ready.append(dep_id)
                    # Re-sort to maintain priority order
                    ready.sort(key=lambda tid: _CATEGORY_PRIORITY.get(topic_map[tid].category, 99))

        # If there are remaining topics (cycle), append them sorted by priority
        if len(sorted_topics) < len(topics):
            remaining = [t for t in topics if t.id not in {s.id for s in sorted_topics}]
            remaining.sort(key=lambda t: _CATEGORY_PRIORITY.get(t.category, 99))
            sorted_topics.extend(remaining)

        return sorted_topics

    # ── Resource validation ────────────────────────────────────────────────────

    @staticmethod
    def _ensure_minimum_resources(topics: list[AIRoadmapTopic]) -> list[AIRoadmapTopic]:
        """Ensure each topic has at least 2 learning resources.

        If a topic has fewer than 2 resources, pad with a documentation resource.
        """
        from app.ai.provider import LearningResource as AILearningResource

        for topic in topics:
            while len(topic.resources) < 2:
                topic.resources.append(
                    AILearningResource(
                        title=f"{topic.skill_name} - Official Documentation",
                        type="documentation",
                        url=None,
                    )
                )
        return topics

    # ── ORM to schema conversion ──────────────────────────────────────────────

    @staticmethod
    def _roadmap_orm_to_schema(roadmap_orm: LearningRoadmapORM) -> LearningRoadmap:
        """Convert a LearningRoadmapORM instance to a LearningRoadmap schema."""
        topics = [
            RoadmapTopic(
                id=topic.id,
                skill_name=topic.skill_name,
                category=topic.category,
                proficiency_target=topic.proficiency_target,
                prerequisites=topic.prerequisites or [],
                resources=[
                    LearningResource(
                        title=res.title,
                        type=res.type,
                        url=res.url,
                    )
                    for res in topic.resources
                ],
                estimated_hours=topic.estimated_hours,
                order=topic.order_index,
            )
            for topic in sorted(roadmap_orm.topics, key=lambda t: t.order_index)
        ]
        return LearningRoadmap(
            id=roadmap_orm.id,
            user_id=roadmap_orm.user_id,
            topics=topics,
            total_weeks=roadmap_orm.total_weeks,
            weekly_study_hours=roadmap_orm.weekly_study_hours,
        )

    # ── Private DB helpers ─────────────────────────────────────────────────────

    async def _get_latest_gap_analysis(self, user_id: UUID) -> SkillGapAnalysisORM | None:
        """Fetch the most recent SkillGapAnalysis for a user with skill_gaps loaded."""
        result = await self._db.execute(
            select(SkillGapAnalysisORM)
            .where(SkillGapAnalysisORM.user_id == user_id)
            .order_by(SkillGapAnalysisORM.analyzed_at.desc())
            .options(selectinload(SkillGapAnalysisORM.skill_gaps))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_roadmap_orm(self, roadmap_id: UUID) -> LearningRoadmapORM | None:
        """Fetch a LearningRoadmap by ID with topics and resources loaded."""
        result = await self._db.execute(
            select(LearningRoadmapORM)
            .where(LearningRoadmapORM.id == roadmap_id)
            .options(
                selectinload(LearningRoadmapORM.topics).selectinload(
                    RoadmapTopicORM.resources
                )
            )
        )
        return result.scalar_one_or_none()

    # ── Public service methods ─────────────────────────────────────────────────

    async def generate_roadmap(
        self, user_id: UUID, weekly_hours: int | None = None
    ) -> LearningRoadmap:
        """Generate a personalised learning roadmap for the user.

        Args:
            user_id: The user's unique identifier.
            weekly_hours: Weekly study hours (1-40). Defaults to 10 if None.

        Returns:
            The generated LearningRoadmap schema.

        Raises:
            InvalidWeeklyHoursError: If weekly_hours is outside 1-40 range.
            NoGapAnalysisError: If user has no skill gap analysis.
        """
        # Default weekly hours
        if weekly_hours is None:
            weekly_hours = 10

        # Validate weekly hours
        self._validate_weekly_hours(weekly_hours)

        # Check prerequisite: gap analysis must exist
        analysis = await self._get_latest_gap_analysis(user_id)
        if analysis is None:
            raise NoGapAnalysisError()

        # Build gaps list for AI provider
        gaps: list[AISkillGap] = [
            AISkillGap(
                skill_name=gap.skill_name,
                category=gap.category,
                current_proficiency=gap.current_proficiency,
                required_proficiency=gap.required_proficiency,
            )
            for gap in analysis.skill_gaps
        ]

        # Call AI provider to generate roadmap topics
        constraints = {"weekly_hours": weekly_hours}
        ai_topics: list[AIRoadmapTopic] = await self._ai_provider.generate_roadmap(
            gaps, constraints
        )

        # Order topics: prerequisites before dependents, prioritize by category
        sorted_topics = self._topological_sort_with_priority(ai_topics)

        # Ensure minimum resources per topic
        sorted_topics = self._ensure_minimum_resources(sorted_topics)

        # Calculate total weeks
        total_hours = sum(t.estimated_hours for t in sorted_topics)
        total_weeks = math.ceil(total_hours / weekly_hours)

        # Persist roadmap ORM
        roadmap_id = uuid.uuid4()
        roadmap_orm = LearningRoadmapORM(
            id=roadmap_id,
            user_id=user_id,
            total_weeks=total_weeks,
            weekly_study_hours=weekly_hours,
        )
        self._db.add(roadmap_orm)
        await self._db.flush()

        # Persist topics and resources
        for order_idx, topic in enumerate(sorted_topics):
            topic_orm = RoadmapTopicORM(
                id=topic.id,
                roadmap_id=roadmap_id,
                skill_name=topic.skill_name,
                category=topic.category,
                proficiency_target=topic.proficiency_target,
                prerequisites=[str(p) for p in topic.prerequisites],
                estimated_hours=topic.estimated_hours,
                order_index=order_idx,
            )
            self._db.add(topic_orm)
            await self._db.flush()

            for resource in topic.resources:
                resource_orm = LearningResourceORM(
                    id=uuid.uuid4(),
                    topic_id=topic.id,
                    title=resource.title,
                    type=resource.type,
                    url=resource.url,
                )
                self._db.add(resource_orm)

        await self._db.flush()

        # Reload with relationships and return schema
        refreshed = await self._get_roadmap_orm(roadmap_id)
        assert refreshed is not None
        return self._roadmap_orm_to_schema(refreshed)

    async def recalculate_timeline(
        self, roadmap_id: UUID, new_weekly_hours: int
    ) -> LearningRoadmap:
        """Recalculate the roadmap timeline proportionally when weekly hours change.

        Args:
            roadmap_id: The roadmap's unique identifier.
            new_weekly_hours: New weekly study hours (1-40).

        Returns:
            The updated LearningRoadmap schema.

        Raises:
            InvalidWeeklyHoursError: If new_weekly_hours is outside 1-40 range.
        """
        # Validate new weekly hours
        self._validate_weekly_hours(new_weekly_hours)

        # Fetch roadmap with topics and resources
        roadmap_orm = await self._get_roadmap_orm(roadmap_id)
        if roadmap_orm is None:
            raise NoGapAnalysisError("Roadmap not found")

        # Recalculate total weeks
        total_hours = sum(topic.estimated_hours for topic in roadmap_orm.topics)
        new_total_weeks = math.ceil(total_hours / new_weekly_hours)

        # Update the roadmap
        roadmap_orm.total_weeks = new_total_weeks
        roadmap_orm.weekly_study_hours = new_weekly_hours
        await self._db.flush()

        return self._roadmap_orm_to_schema(roadmap_orm)

    async def get_roadmap(self, user_id: UUID) -> LearningRoadmap | None:
        """Fetch the latest roadmap for the user with topics and resources loaded.

        Returns:
            The LearningRoadmap schema or None if no roadmap exists.
        """
        result = await self._db.execute(
            select(LearningRoadmapORM)
            .where(LearningRoadmapORM.user_id == user_id)
            .order_by(LearningRoadmapORM.created_at.desc())
            .options(
                selectinload(LearningRoadmapORM.topics).selectinload(
                    RoadmapTopicORM.resources
                )
            )
            .limit(1)
        )
        roadmap_orm = result.scalar_one_or_none()
        if roadmap_orm is None:
            return None
        return self._roadmap_orm_to_schema(roadmap_orm)
