"""Target role selection and requirements routes."""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.openai_provider import OpenAIProvider
from app.api.deps import get_current_user_id
from app.core.database import get_db
from app.schemas.target_role import (
    CustomRoleInput,
    SkillRequirement,
    TargetRole,
    TargetRoleRequirements,
)
from app.services.target_role_service import TargetRoleService

router = APIRouter()


# ── Request body models ────────────────────────────────────────────────────────


class SetTargetRoleInput(BaseModel):
    """Request body for setting a recognized target role."""

    role_title: str = Field(max_length=100)


class UpdateSkillsInput(BaseModel):
    """Request body for updating target role skills."""

    skills: list[SkillRequirement]


# ── Dependency helpers ─────────────────────────────────────────────────────────


def get_target_role_service(
    db: AsyncSession = Depends(get_db),
) -> TargetRoleService:
    """Dependency that constructs a TargetRoleService with the current DB session and AI provider."""
    ai_provider = OpenAIProvider()
    return TargetRoleService(db=db, ai_provider=ai_provider)


# ── Endpoints ──────────────────────────────────────────────────────────────────


@router.post("", response_model=TargetRole, summary="Set a recognised target role")
async def set_target_role(
    body: SetTargetRoleInput,
    user_id: UUID = Depends(get_current_user_id),
    service: TargetRoleService = Depends(get_target_role_service),
) -> TargetRole:
    """Set the user's target role by choosing from recognised roles.

    The AI provider identifies the required skills for the role.
    If fewer than 5 skills are returned, the role is marked as unrecognized.

    Requirements: 2.1, 2.2
    """
    return await service.set_target_role(user_id=user_id, role_title=body.role_title)


@router.get(
    "/requirements",
    response_model=TargetRoleRequirements,
    summary="Get skill requirements for target role",
)
async def get_requirements(
    role_title: str | None = None,
    user_id: UUID = Depends(get_current_user_id),
    service: TargetRoleService = Depends(get_target_role_service),
) -> TargetRoleRequirements:
    """Retrieve skill requirements for a role.

    When ``role_title`` is provided, the AI is queried directly and the result
    is returned without touching the database (preview / search mode).

    When ``role_title`` is omitted, the user's already-saved target role is
    returned instead.

    Requirements: 2.3
    """
    if role_title:
        return await service.preview_role_requirements(role_title=role_title.strip())
    return await service.get_target_role_requirements(user_id=user_id)


@router.put("/skills", response_model=TargetRole, summary="Update skills for target role")
async def update_skills(
    body: UpdateSkillsInput,
    user_id: UUID = Depends(get_current_user_id),
    service: TargetRoleService = Depends(get_target_role_service),
) -> TargetRole:
    """Update the skill requirements associated with the target role.

    Requirements: 2.4
    """
    return await service.update_target_role_skills(user_id=user_id, skills=body.skills)


@router.post("/custom", response_model=TargetRole, summary="Set a custom target role")
async def set_custom_role(
    body: CustomRoleInput,
    user_id: UUID = Depends(get_current_user_id),
    service: TargetRoleService = Depends(get_target_role_service),
) -> TargetRole:
    """Define a fully custom target role with user-specified skills.

    Used when the AI does not recognize the role title (fewer than 5 skills returned).
    The user provides their own skill requirements and responsibilities description.

    Requirements: 2.5
    """
    return await service.set_custom_role(user_id=user_id, data=body)
