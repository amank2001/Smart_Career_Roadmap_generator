"""Error code constants and structured error response model."""

from pydantic import BaseModel


# ── Input validation error codes ───────────────────────────────────────────────

JOB_TITLE_TOO_LONG = "JOB_TITLE_TOO_LONG"
INVALID_EXPERIENCE = "INVALID_EXPERIENCE"
INVALID_SKILL_COUNT = "INVALID_SKILL_COUNT"
SKILL_NAME_TOO_LONG = "SKILL_NAME_TOO_LONG"
INVALID_ROLE_TITLE = "INVALID_ROLE_TITLE"
INVALID_WEEKLY_HOURS = "INVALID_WEEKLY_HOURS"
OUTCOME_TOO_LONG = "OUTCOME_TOO_LONG"

# ── File upload error codes ────────────────────────────────────────────────────

UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
FILE_TOO_LARGE = "FILE_TOO_LARGE"
EXTRACTION_FAILED = "EXTRACTION_FAILED"

# ── Prerequisite error codes ───────────────────────────────────────────────────

INCOMPLETE_PROFILE = "INCOMPLETE_PROFILE"
NO_TARGET_ROLE = "NO_TARGET_ROLE"
MISSING_PREREQUISITE = "MISSING_PREREQUISITE"
NO_GAP_ANALYSIS = "NO_GAP_ANALYSIS"

# ── AI service error codes ─────────────────────────────────────────────────────

AI_TIMEOUT = "AI_TIMEOUT"
AI_UNAVAILABLE = "AI_UNAVAILABLE"
AI_RESPONSE_ERROR = "AI_RESPONSE_ERROR"


# ── Structured error response ──────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    """Standard error response body returned for all domain errors."""

    error: str
    message: str
