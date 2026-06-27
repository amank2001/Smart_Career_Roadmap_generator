"""Domain-specific exceptions and FastAPI exception handlers."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


# ── Domain exceptions ──────────────────────────────────────────────────────────

class DomainError(Exception):
    """Base class for all domain errors."""

    error_code: str = "DOMAIN_ERROR"
    status_code: int = 422
    message: str = "A domain error occurred."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.__class__.message
        super().__init__(self.message)


class IncompleteProfileError(DomainError):
    error_code = "INCOMPLETE_PROFILE"
    status_code = 422
    message = "Please complete your profile with at least a job title and one skill"


class NoTargetRoleError(DomainError):
    error_code = "NO_TARGET_ROLE"
    status_code = 422
    message = "Please select a target role before running gap analysis"


class NoGapAnalysisError(DomainError):
    error_code = "NO_GAP_ANALYSIS"
    status_code = 422
    message = "Please run a skill gap analysis first"


class MissingPrerequisiteError(DomainError):
    error_code = "MISSING_PREREQUISITE"
    status_code = 422
    message = "A required prerequisite is missing"


class JobTitleTooLongError(DomainError):
    error_code = "JOB_TITLE_TOO_LONG"
    status_code = 422
    message = "Job title must not exceed 100 characters"


class InvalidExperienceError(DomainError):
    error_code = "INVALID_EXPERIENCE"
    status_code = 422
    message = "Years of experience must be between 0 and 50"


class InvalidSkillCountError(DomainError):
    error_code = "INVALID_SKILL_COUNT"
    status_code = 422
    message = "Skills list must contain between 1 and 50 items"


class SkillNameTooLongError(DomainError):
    error_code = "SKILL_NAME_TOO_LONG"
    status_code = 422
    message = "Skill name must not exceed 60 characters"


class UnsupportedFormatError(DomainError):
    error_code = "UNSUPPORTED_FORMAT"
    status_code = 415
    message = "Supported formats: PDF, DOCX, plain text"


class FileTooLargeError(DomainError):
    error_code = "FILE_TOO_LARGE"
    status_code = 413
    message = "Maximum file size is 5 MB"


class ExtractionFailedError(DomainError):
    error_code = "EXTRACTION_FAILED"
    status_code = 422
    message = (
        "Could not extract information from the document. "
        "Please re-upload or enter information manually."
    )


class InvalidRoleTitleError(DomainError):
    error_code = "INVALID_ROLE_TITLE"
    status_code = 422
    message = "Role title must be 1-100 characters"


class InvalidCustomRoleError(DomainError):
    error_code = "INVALID_CUSTOM_ROLE"
    status_code = 422
    message = "Custom role requires at least 3 skills and a non-empty responsibilities description"


class InvalidWeeklyHoursError(DomainError):
    error_code = "INVALID_WEEKLY_HOURS"
    status_code = 422
    message = "Weekly study hours must be between 1 and 40"


class OutcomeTooLongError(DomainError):
    error_code = "OUTCOME_TOO_LONG"
    status_code = 422
    message = "Outcome description must be 500 characters or fewer"


class ProjectNotFoundError(DomainError):
    error_code = "PROJECT_NOT_FOUND"
    status_code = 404
    message = "Project not found"


class AITimeoutError(DomainError):
    error_code = "AI_TIMEOUT"
    status_code = 504
    message = "The analysis is taking longer than expected. Please try again."


class AIUnavailableError(DomainError):
    error_code = "AI_UNAVAILABLE"
    status_code = 503
    message = "The AI service is temporarily unavailable. Please try again later."


class AIResponseError(DomainError):
    error_code = "AI_RESPONSE_ERROR"
    status_code = 500
    message = "An unexpected error occurred during analysis. Please try again."


# ── Exception handlers ─────────────────────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    """Register all domain exception handlers on the FastAPI app."""

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.error_code, "message": exc.message},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": "VALIDATION_ERROR",
                "message": "Input validation failed",
                "details": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
            },
        )
