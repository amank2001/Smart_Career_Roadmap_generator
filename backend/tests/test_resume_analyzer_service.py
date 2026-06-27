"""Tests for ResumeAnalyzerService.

Covers:
- validate_file_format: valid formats (PDF, DOCX, TXT)
- validate_file_format: unsupported formats (exe, jpeg)
- validate_file_format: file exceeding 5 MB limit
- get_supported_formats: expected list
- analyze_resume: success path (mocked AI provider)
- analyze_resume: AI provider raises exception → ExtractionFailedError
- analyze_resume: invalid file format → UnsupportedFormatError
- analyze_resume: file too large → FileTooLargeError
"""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock

import pytest
import docx
import pdfplumber  # noqa: F401  (checked at import time)

from app.core.exceptions import (
    ExtractionFailedError,
    FileTooLargeError,
    UnsupportedFormatError,
)
from app.services.protocols import UploadedFile
from app.services.resume_analyzer_service import MAX_FILE_SIZE_BYTES, ResumeAnalyzerService


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_file(
    content: bytes = b"dummy",
    mime_type: str = "text/plain",
    original_name: str = "resume.txt",
    size_bytes: int | None = None,
) -> UploadedFile:
    """Build a minimal UploadedFile for testing."""
    return UploadedFile(
        content=content,
        mime_type=mime_type,
        original_name=original_name,
        size_bytes=size_bytes if size_bytes is not None else len(content),
    )


_SENTINEL = object()


def _make_mock_ai(result: dict | None = _SENTINEL, raises: Exception | None = None) -> AsyncMock:  # type: ignore[assignment]
    """Return a mock AIProvider whose analyze_resume behaves as specified."""
    provider = MagicMock()
    if raises is not None:
        provider.analyze_resume = AsyncMock(side_effect=raises)
    else:
        if result is _SENTINEL:
            result = {
                "skills": ["Python"],
                "job_history": [{"title": "Dev", "company": "ACME", "years": 2}],
                "years_of_experience": 2,
            }
        provider.analyze_resume = AsyncMock(return_value=result)
    return provider


def _make_service(ai=None) -> ResumeAnalyzerService:
    if ai is None:
        ai = _make_mock_ai()
    return ResumeAnalyzerService(ai_provider=ai)


def _make_minimal_docx() -> bytes:
    """Return the bytes of a minimal valid DOCX containing one paragraph."""
    doc = docx.Document()
    doc.add_paragraph("Software Engineer with 5 years of Python experience.")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _make_minimal_pdf() -> bytes:
    """Return the bytes of a minimal valid PDF using only stdlib (no reportlab needed).

    We embed a hand-crafted PDF so the test has zero extra dependencies.
    pdfplumber should be able to parse it and extract the text.
    """
    # Minimal single-page PDF with one text stream
    content = b"""%PDF-1.4
1 0 obj<</Type /Catalog /Pages 2 0 R>>endobj
2 0 obj<</Type /Pages /Kids [3 0 R] /Count 1>>endobj
3 0 obj<</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
/Contents 4 0 R /Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 44>>
stream
BT /F1 12 Tf 100 700 Td (Resume Text) Tj ET
endstream
endobj
5 0 obj<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000266 00000 n 
0000000360 00000 n 
trailer<</Size 6 /Root 1 0 R>>
startxref
441
%%EOF"""
    return content


# ── validate_file_format ───────────────────────────────────────────────────────


class TestValidateFileFormat:
    """Tests for the synchronous validate_file_format method."""

    def test_valid_pdf_by_mime(self):
        svc = _make_service()
        result = svc.validate_file_format(_make_file(mime_type="application/pdf", original_name="cv.pdf"))
        assert result.valid is True
        assert result.error is None

    def test_valid_docx_by_mime(self):
        svc = _make_service()
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        result = svc.validate_file_format(_make_file(mime_type=mime, original_name="cv.docx"))
        assert result.valid is True
        assert result.error is None

    def test_valid_txt_by_mime(self):
        svc = _make_service()
        result = svc.validate_file_format(_make_file(mime_type="text/plain", original_name="cv.txt"))
        assert result.valid is True
        assert result.error is None

    def test_valid_pdf_by_extension_fallback(self):
        """If MIME is generic octet-stream but extension is .pdf, treat as PDF."""
        svc = _make_service()
        result = svc.validate_file_format(
            _make_file(mime_type="application/octet-stream", original_name="cv.pdf")
        )
        assert result.valid is True

    def test_valid_docx_by_extension_fallback(self):
        svc = _make_service()
        result = svc.validate_file_format(
            _make_file(mime_type="application/octet-stream", original_name="cv.docx")
        )
        assert result.valid is True

    def test_valid_txt_by_extension_fallback(self):
        svc = _make_service()
        result = svc.validate_file_format(
            _make_file(mime_type="application/octet-stream", original_name="cv.txt")
        )
        assert result.valid is True

    def test_unsupported_exe(self):
        svc = _make_service()
        result = svc.validate_file_format(
            _make_file(mime_type="application/x-msdownload", original_name="virus.exe")
        )
        assert result.valid is False
        assert result.error == "UNSUPPORTED_FORMAT"

    def test_unsupported_jpeg(self):
        svc = _make_service()
        result = svc.validate_file_format(
            _make_file(mime_type="image/jpeg", original_name="photo.jpg")
        )
        assert result.valid is False
        assert result.error == "UNSUPPORTED_FORMAT"

    def test_unsupported_unknown_extension(self):
        svc = _make_service()
        result = svc.validate_file_format(
            _make_file(mime_type="application/octet-stream", original_name="file.xyz")
        )
        assert result.valid is False
        assert result.error == "UNSUPPORTED_FORMAT"

    def test_file_too_large(self):
        svc = _make_service()
        big_size = MAX_FILE_SIZE_BYTES + 1
        result = svc.validate_file_format(
            _make_file(mime_type="application/pdf", original_name="big.pdf", size_bytes=big_size)
        )
        assert result.valid is False
        assert result.error == "FILE_TOO_LARGE"

    def test_exactly_at_size_limit_is_valid(self):
        svc = _make_service()
        result = svc.validate_file_format(
            _make_file(
                mime_type="application/pdf",
                original_name="exact.pdf",
                size_bytes=MAX_FILE_SIZE_BYTES,
            )
        )
        assert result.valid is True

    def test_unsupported_format_takes_priority_over_large_size(self):
        """UNSUPPORTED_FORMAT is returned even when the file is also too large."""
        svc = _make_service()
        big_size = MAX_FILE_SIZE_BYTES + 1
        result = svc.validate_file_format(
            _make_file(
                mime_type="image/png",
                original_name="big.png",
                size_bytes=big_size,
            )
        )
        assert result.valid is False
        assert result.error == "UNSUPPORTED_FORMAT"


# ── get_supported_formats ──────────────────────────────────────────────────────


class TestGetSupportedFormats:
    def test_returns_expected_formats(self):
        svc = _make_service()
        formats = svc.get_supported_formats()
        assert sorted(formats) == ["docx", "pdf", "txt"]

    def test_returns_list(self):
        svc = _make_service()
        assert isinstance(svc.get_supported_formats(), list)


# ── analyze_resume ─────────────────────────────────────────────────────────────


class TestAnalyzeResume:
    """Tests for the async analyze_resume method."""

    @pytest.mark.asyncio
    async def test_success_txt(self):
        """Plain text file is parsed and AI result is returned."""
        ai = _make_mock_ai(
            result={
                "skills": ["Python", "FastAPI"],
                "job_history": [{"title": "Engineer", "company": "Corp", "years": 3}],
                "years_of_experience": 3,
            }
        )
        svc = _make_service(ai)
        file = _make_file(
            content=b"Software Engineer at Corp for 3 years. Skills: Python, FastAPI.",
            mime_type="text/plain",
            original_name="resume.txt",
        )
        result = await svc.analyze_resume(file)
        assert result.success is True
        assert result.extracted_data is not None
        assert "skills" in result.extracted_data
        assert "years_of_experience" in result.extracted_data

    @pytest.mark.asyncio
    async def test_success_docx(self):
        """DOCX file is parsed and AI result is returned."""
        ai = _make_mock_ai()
        svc = _make_service(ai)
        file = _make_file(
            content=_make_minimal_docx(),
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            original_name="resume.docx",
        )
        result = await svc.analyze_resume(file)
        assert result.success is True
        assert result.extracted_data is not None
        # Confirm AI was called exactly once with 'docx' as the second positional arg
        ai.analyze_resume.assert_called_once()
        call_args = ai.analyze_resume.call_args
        # Handles both positional (args) and keyword (kwargs) invocations
        positional = call_args.args
        kwargs = call_args.kwargs
        fmt_arg = positional[1] if len(positional) >= 2 else kwargs.get("format") or kwargs.get("fmt")
        assert fmt_arg == "docx"

    @pytest.mark.asyncio
    async def test_success_pdf(self):
        """PDF file is parsed and AI result is returned."""
        ai = _make_mock_ai()
        svc = _make_service(ai)
        pdf_bytes = _make_minimal_pdf()
        file = _make_file(
            content=pdf_bytes,
            mime_type="application/pdf",
            original_name="resume.pdf",
            size_bytes=len(pdf_bytes),
        )
        result = await svc.analyze_resume(file)
        assert result.success is True
        assert result.extracted_data is not None

    @pytest.mark.asyncio
    async def test_ai_exception_raises_extraction_failed(self):
        """When AI provider raises any exception, ExtractionFailedError is raised."""
        ai = _make_mock_ai(raises=RuntimeError("OpenAI timeout"))
        svc = _make_service(ai)
        file = _make_file(
            content=b"Some resume text.",
            mime_type="text/plain",
            original_name="resume.txt",
        )
        with pytest.raises(ExtractionFailedError):
            await svc.analyze_resume(file)

    @pytest.mark.asyncio
    async def test_ai_returns_empty_dict_raises_extraction_failed(self):
        """When AI provider returns an empty dict, ExtractionFailedError is raised."""
        ai = _make_mock_ai(result={})
        svc = _make_service(ai)
        file = _make_file(
            content=b"Some resume text.",
            mime_type="text/plain",
            original_name="resume.txt",
        )
        with pytest.raises(ExtractionFailedError):
            await svc.analyze_resume(file)

    @pytest.mark.asyncio
    async def test_ai_returns_none_raises_extraction_failed(self):
        """When AI provider returns None, ExtractionFailedError is raised."""
        ai = _make_mock_ai(result=None)
        # Override to actually return None
        ai.analyze_resume = AsyncMock(return_value=None)
        svc = _make_service(ai)
        file = _make_file(
            content=b"Some resume text.",
            mime_type="text/plain",
            original_name="resume.txt",
        )
        with pytest.raises(ExtractionFailedError):
            await svc.analyze_resume(file)

    @pytest.mark.asyncio
    async def test_unsupported_format_raises_domain_error(self):
        """Passing a JPEG raises UnsupportedFormatError."""
        svc = _make_service()
        file = _make_file(
            content=b"\xff\xd8\xff",
            mime_type="image/jpeg",
            original_name="photo.jpg",
        )
        with pytest.raises(UnsupportedFormatError):
            await svc.analyze_resume(file)

    @pytest.mark.asyncio
    async def test_file_too_large_raises_domain_error(self):
        """A PDF that exceeds 5 MB raises FileTooLargeError."""
        svc = _make_service()
        file = _make_file(
            content=b"fake pdf content",
            mime_type="application/pdf",
            original_name="large.pdf",
            size_bytes=MAX_FILE_SIZE_BYTES + 1,
        )
        with pytest.raises(FileTooLargeError):
            await svc.analyze_resume(file)

    @pytest.mark.asyncio
    async def test_txt_format_passed_to_ai(self):
        """The format string 'txt' is forwarded to the AI provider."""
        ai = _make_mock_ai()
        svc = _make_service(ai)
        file = _make_file(
            content=b"Engineer with 5 years experience.",
            mime_type="text/plain",
            original_name="resume.txt",
        )
        await svc.analyze_resume(file)
        ai.analyze_resume.assert_called_once()
        call_args = ai.analyze_resume.call_args
        positional = call_args.args
        kwargs = call_args.kwargs
        fmt_arg = positional[1] if len(positional) >= 2 else kwargs.get("format") or kwargs.get("fmt")
        assert fmt_arg == "txt"
