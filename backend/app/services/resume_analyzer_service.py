"""Concrete implementation of the ResumeAnalyzerService protocol.

Supports PDF (via pdfplumber), DOCX (via python-docx), and plain-text (.txt)
resume uploads up to 5 MB. Delegates AI extraction to an AIProvider.
"""

from __future__ import annotations

import io
import logging

import pdfplumber
import docx  # python-docx

from app.ai.provider import AIProvider
from app.core.exceptions import (
    ExtractionFailedError,
    FileTooLargeError,
    UnsupportedFormatError,
)
from app.services.protocols import (
    ResumeAnalysisResultModel,
    UploadedFile,
    ValidationResultModel,
)

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

MAX_FILE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB

# Mapping from supported MIME types → canonical format name
_MIME_TO_FORMAT: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
}

# Mapping from file extension (lower-case, with leading dot) → canonical format name
_EXT_TO_FORMAT: dict[str, str] = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "txt",
}


# ── Service ────────────────────────────────────────────────────────────────────


class ResumeAnalyzerService:
    """Extract structured career data from an uploaded resume file.

    Injectable via FastAPI ``Depends``; accepts an ``AIProvider`` in the
    constructor so the AI backend can be swapped or mocked in tests.
    """

    def __init__(self, ai_provider: AIProvider) -> None:
        self._ai = ai_provider

    # ── Public interface ───────────────────────────────────────────────────────

    def get_supported_formats(self) -> list[str]:
        """Return the list of supported format names: ['pdf', 'docx', 'txt']."""
        return ["pdf", "docx", "txt"]

    def validate_file_format(self, file: UploadedFile) -> ValidationResultModel:
        """Validate mime type / extension and file size.

        Format is checked before size so that an unsupported-format error takes
        priority over a size error when both conditions apply.

        Returns:
            ValidationResultModel(valid=True) on success.
            ValidationResultModel(valid=False, error="UNSUPPORTED_FORMAT") for
              unrecognised file types.
            ValidationResultModel(valid=False, error="FILE_TOO_LARGE") when size
              exceeds 5 MB.
        """
        fmt = self._resolve_format(file)
        if fmt is None:
            return ValidationResultModel(valid=False, error="UNSUPPORTED_FORMAT")

        if file.size_bytes > MAX_FILE_SIZE_BYTES:
            return ValidationResultModel(valid=False, error="FILE_TOO_LARGE")

        return ValidationResultModel(valid=True)

    async def analyze_resume(self, file: UploadedFile) -> ResumeAnalysisResultModel:
        """Parse and analyse a resume file.

        Steps:
        1. Validate format & size; raise the appropriate domain error on failure.
        2. Extract plain text from the file content.
        3. Call the AI provider to extract structured data.
        4. Return a ResumeAnalysisResultModel on success.

        Raises:
            UnsupportedFormatError: file is not PDF / DOCX / TXT.
            FileTooLargeError: file exceeds 5 MB.
            ExtractionFailedError: text extraction or AI call failed.
        """
        # Step 1 – validate (format first, then size)
        validation = self.validate_file_format(file)
        if not validation.valid:
            if validation.error == "UNSUPPORTED_FORMAT":
                raise UnsupportedFormatError()
            if validation.error == "FILE_TOO_LARGE":
                raise FileTooLargeError()
            raise UnsupportedFormatError()  # fallback

        fmt = self._resolve_format(file)
        assert fmt is not None  # guaranteed by validation above

        # Step 2 – extract text
        try:
            text_content = self._extract_text(file.content, fmt)
        except Exception as exc:
            logger.warning("Text extraction failed for %s: %s", file.original_name, exc)
            raise ExtractionFailedError() from exc

        if not text_content or not text_content.strip():
            raise ExtractionFailedError("Document appears to be empty.")

        # Step 3 – call AI provider; wrap *all* exceptions as ExtractionFailedError
        try:
            result = await self._ai.analyze_resume(text_content, fmt)
        except Exception as exc:
            logger.warning("AI extraction failed for %s: %s", file.original_name, exc)
            raise ExtractionFailedError() from exc

        if not result:
            raise ExtractionFailedError("AI returned empty analysis result.")

        # Step 4 – return success
        return ResumeAnalysisResultModel(success=True, extracted_data=result)

    # ── Private helpers ────────────────────────────────────────────────────────

    def _resolve_format(self, file: UploadedFile) -> str | None:
        """Return the canonical format string, or None if unsupported."""
        # Try MIME type first
        fmt = _MIME_TO_FORMAT.get(file.mime_type.lower().strip())
        if fmt:
            return fmt

        # Fall back to file extension
        name = file.original_name.lower().strip()
        for ext, fmt_name in _EXT_TO_FORMAT.items():
            if name.endswith(ext):
                return fmt_name

        return None

    @staticmethod
    def _extract_text(content: bytes, fmt: str) -> str:
        """Extract plain text from file bytes for the given format string."""
        if fmt == "pdf":
            return ResumeAnalyzerService._extract_pdf(content)
        if fmt == "docx":
            return ResumeAnalyzerService._extract_docx(content)
        if fmt == "txt":
            return content.decode("utf-8", errors="replace")
        raise ValueError(f"Unsupported format for extraction: {fmt}")

    @staticmethod
    def _extract_pdf(content: bytes) -> str:
        """Extract text from PDF bytes using pdfplumber."""
        pages: list[str] = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
        return "\n".join(pages)

    @staticmethod
    def _extract_docx(content: bytes) -> str:
        """Extract text from DOCX bytes using python-docx."""
        doc = docx.Document(io.BytesIO(content))
        paragraphs = [para.text for para in doc.paragraphs if para.text]
        return "\n".join(paragraphs)
