"""Top-level API router that aggregates all domain sub-routers."""

from fastapi import APIRouter

from app.api.routes import (
    auth,
    interview,
    profile,
    progress,
    projects,
    roadmap,
    skill_gap,
    target_role,
    weekly_plans,
)

api_router = APIRouter()

# ── Health ────────────────────────────────────────────────────────────────────

@api_router.get("/health", tags=["health"])
async def health_check() -> dict:
    return {"status": "ok"}

# ── Domain routers ─────────────────────────────────────────────────────────────

api_router.include_router(auth.router,         prefix="/auth",         tags=["auth"])
api_router.include_router(profile.router,      prefix="/profile",      tags=["profile"])
api_router.include_router(target_role.router,  prefix="/target-role",  tags=["target-role"])
api_router.include_router(skill_gap.router,    prefix="/skill-gap",    tags=["skill-gap"])
api_router.include_router(roadmap.router,      prefix="/roadmap",      tags=["roadmap"])
api_router.include_router(weekly_plans.router, prefix="/weekly-plans", tags=["weekly-plans"])
api_router.include_router(interview.router,    prefix="/interview",    tags=["interview"])
api_router.include_router(projects.router,     prefix="/projects",     tags=["projects"])
api_router.include_router(progress.router,     prefix="/progress",     tags=["progress"])
