"""Profile management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.openai_provider import OpenAIProvider
from app.api.deps import get_current_user_id
from app.core.database import get_db
from app.schemas.profile import CreateProfileInput, Profile, UpdateProfileInput
from app.services.profile_service import ProfileService
from app.services.protocols import ResumeAnalysisResultModel, UploadedFile
from app.services.resume_analyzer_service import ResumeAnalyzerService

router = APIRouter()


# ── Dependency helpers ─────────────────────────────────────────────────────────

def get_profile_service(db: AsyncSession = Depends(get_db)) -> ProfileService:
    """Dependency that constructs a ProfileService with the current DB session."""
    return ProfileService(db=db)


def get_resume_analyzer_service() -> ResumeAnalyzerService:
    """Dependency that constructs a ResumeAnalyzerService with the default AI provider."""
    ai_provider = OpenAIProvider()
    return ResumeAnalyzerService(ai_provider=ai_provider)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=Profile,
    status_code=status.HTTP_200_OK,
    summary="Create user profile",
)
async def create_profile(
    body: CreateProfileInput,
    user_id: UUID = Depends(get_current_user_id),
    service: ProfileService = Depends(get_profile_service),
) -> Profile:
    """Create a new profile for the authenticated user.

    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
    """
    return await service.create_profile(user_id=user_id, data=body)


@router.put(
    "",
    response_model=Profile,
    status_code=status.HTTP_200_OK,
    summary="Update user profile",
)
async def update_profile(
    body: UpdateProfileInput,
    user_id: UUID = Depends(get_current_user_id),
    service: ProfileService = Depends(get_profile_service),
) -> Profile:
    """Update the profile for the authenticated user.

    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
    """
    return await service.update_profile(user_id=user_id, data=body)


@router.get(
    "",
    response_model=Profile,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
)
async def get_profile(
    user_id: UUID = Depends(get_current_user_id),
    service: ProfileService = Depends(get_profile_service),
) -> Profile:
    """Retrieve the current authenticated user's profile.

    Returns 404 if no profile exists yet.

    Requirements: 1.1, 1.6
    """
    profile = await service.get_profile(user_id=user_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "PROFILE_NOT_FOUND", "message": "No profile found for this user"},
        )
    return profile


@router.post(
    "/resume",
    response_model=ResumeAnalysisResultModel,
    status_code=status.HTTP_200_OK,
    summary="Upload resume for profile extraction",
)
async def upload_resume(
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user_id),
    analyzer: ResumeAnalyzerService = Depends(get_resume_analyzer_service),
) -> ResumeAnalysisResultModel:
    """Upload a resume (PDF/DOCX/plain text) and extract profile information.

    Returns extracted data for the user to review and confirm before saving.
    Does NOT automatically update the profile.

    Requirements: 1.7
    """
    content = await file.read()
    uploaded = UploadedFile(
        content=content,
        mime_type=file.content_type or "application/octet-stream",
        original_name=file.filename or "resume",
        size_bytes=len(content),
    )
    # Raises FileTooLargeError, UnsupportedFormatError, or ExtractionFailedError
    # which are handled by the registered DomainError exception handler
    return await analyzer.analyze_resume(file=uploaded)
