"""Orchestrates one document analysis: save to a private temp file, extract, classify, derive insights.

The uploaded bytes live only in a temporary file that is removed in a ``finally`` block,
whether processing succeeds or fails. Full extracted text is never returned for storage.
"""
from __future__ import annotations

import os
import secrets
import time
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from ..config import settings
from .classifier import get_classifier
from .extraction import ExtractionError, extract_text, safe_display_name
from .insights import assess_priority, extract_fields, extract_keywords, summarize
from .text_utils import words

CHUNK = 64 * 1024


class UploadTooLarge(Exception):
    pass


@dataclass
class AnalysisResult:
    filename: str
    file_type: str
    file_size: int
    page_count: int | None
    word_count: int
    char_count: int
    truncated: bool
    prediction: dict
    summary: str
    keywords: list[dict]
    extracted_fields: dict
    priority: str
    priority_reasons: list[str]
    processing_ms: int


async def _spool_to_temp(upload: UploadFile, temp_dir: Path, max_bytes: int) -> tuple[Path, int]:
    temp_dir.mkdir(parents=True, exist_ok=True)
    # Random name: the user-supplied filename is never used on disk.
    path = temp_dir / f"upload-{secrets.token_hex(16)}.bin"
    size = 0
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
    try:
        with os.fdopen(fd, "wb") as out:
            while chunk := await upload.read(CHUNK):
                size += len(chunk)
                if size > max_bytes:
                    raise UploadTooLarge()
                out.write(chunk)
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path, size


def analyze_text(text: str) -> dict:
    """Run the ML model and all insight extractors on already-extracted text."""
    clf = get_classifier()
    word_count = len(words(text))
    prediction = clf.predict(text, word_count)
    priority, priority_reasons = assess_priority(text, prediction["category"], prediction["is_uncertain"])
    return {
        "word_count": word_count,
        "prediction": prediction,
        "summary": summarize(text),
        "keywords": extract_keywords(text, clf.idf, clf.max_idf),
        "extracted_fields": extract_fields(text),
        "priority": priority,
        "priority_reasons": priority_reasons,
    }


async def analyze_upload(upload: UploadFile) -> AnalysisResult:
    started = time.perf_counter()
    display_name = safe_display_name(upload.filename)
    path, size = await _spool_to_temp(upload, settings.temp_dir, settings.max_upload_bytes)
    try:
        if size == 0:
            raise ExtractionError("The uploaded file is empty.")
        doc = extract_text(path, display_name, max_pages=settings.max_pdf_pages, max_chars=settings.max_text_chars)
        result = analyze_text(doc.text)
    finally:
        path.unlink(missing_ok=True)

    return AnalysisResult(
        filename=display_name,
        file_type=doc.file_type,
        file_size=size,
        page_count=doc.page_count,
        word_count=result["word_count"],
        char_count=len(doc.text),
        truncated=doc.truncated,
        prediction=result["prediction"],
        summary=result["summary"],
        keywords=result["keywords"],
        extracted_fields=result["extracted_fields"],
        priority=result["priority"],
        priority_reasons=result["priority_reasons"],
        processing_ms=int((time.perf_counter() - started) * 1000),
    )
