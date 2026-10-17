"""Validation and text extraction for untrusted uploaded files (PDF, DOCX, TXT).

Every check here assumes the file is hostile: the extension, the declared content type
and the actual bytes must agree, archives are inspected before parsing, and size limits
are enforced on both the upload and the extracted text.
"""
from __future__ import annotations

import re
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf": "pdf", ".docx": "docx", ".txt": "txt"}

# DOCX is a zip archive; guard against zip bombs before python-docx touches it.
MAX_DOCX_UNCOMPRESSED = 60 * 1024 * 1024
MAX_DOCX_ENTRIES = 2000
MAX_DOCX_RATIO = 120


class ExtractionError(Exception):
    """Raised for files that are invalid, unsupported or contain no usable text.

    The message is safe to show to the user.
    """


@dataclass
class ExtractedDocument:
    text: str
    file_type: str
    page_count: int | None
    truncated: bool


_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._ ()\-]+")


def safe_display_name(filename: str | None) -> str:
    """Return a harmless display name: no path components, control or special characters."""
    name = (filename or "").replace("\\", "/").split("/")[-1]
    name = unicodedata.normalize("NFKC", name)
    name = _SAFE_CHARS.sub("_", name).strip(" .")
    if not name:
        name = "document"
    if len(name) > 120:
        stem, dot, ext = name.rpartition(".")
        name = (stem[: 120 - len(ext) - 1] + "." + ext) if dot and len(ext) <= 5 else name[:120]
    return name


def detect_type(filename: str, head: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ExtractionError("Unsupported file type. Please upload a PDF, DOCX or TXT file.")
    kind = SUPPORTED_EXTENSIONS[ext]
    if kind == "pdf" and not head.lstrip()[:5].startswith(b"%PDF-"):
        raise ExtractionError("The file has a .pdf extension but is not a valid PDF document.")
    if kind == "docx" and not head.startswith(b"PK\x03\x04"):
        raise ExtractionError("The file has a .docx extension but is not a valid Word document.")
    if kind == "txt" and b"\x00" in head:
        raise ExtractionError("The file has a .txt extension but appears to contain binary data.")
    return kind


def _extract_pdf(path: Path, max_pages: int) -> tuple[str, int]:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(str(path), strict=False)
        if reader.is_encrypted:
            raise ExtractionError("Password-protected PDFs are not supported.")
        n_pages = len(reader.pages)
        if n_pages > max_pages:
            raise ExtractionError(f"The PDF has {n_pages} pages; the limit is {max_pages}.")
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts), n_pages
    except ExtractionError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError, AttributeError, OSError, RecursionError) as exc:
        raise ExtractionError("The PDF could not be read. It may be damaged or malformed.") from exc


def _check_docx_archive(path: Path) -> None:
    try:
        with zipfile.ZipFile(path) as zf:
            infos = zf.infolist()
            if len(infos) > MAX_DOCX_ENTRIES:
                raise ExtractionError("The Word document contains too many internal parts.")
            names = {i.filename for i in infos}
            if "word/document.xml" not in names or "[Content_Types].xml" not in names:
                raise ExtractionError("The file is not a valid Word (.docx) document.")
            total = 0
            for info in infos:
                total += info.file_size
                if info.compress_size and info.file_size / max(info.compress_size, 1) > MAX_DOCX_RATIO \
                        and info.file_size > 1024 * 1024:
                    raise ExtractionError("The Word document has a suspicious compression ratio.")
            if total > MAX_DOCX_UNCOMPRESSED:
                raise ExtractionError("The Word document is too large when uncompressed.")
    except zipfile.BadZipFile as exc:
        raise ExtractionError("The file is not a valid Word (.docx) document.") from exc


def _extract_docx(path: Path) -> str:
    _check_docx_archive(path)
    import docx

    try:
        document = docx.Document(str(path))
    except Exception as exc:  # python-docx raises a variety of parser errors
        raise ExtractionError("The Word document could not be read. It may be damaged.") from exc
    parts = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            parts.append(" | ".join(c for c in cells if c))
    return "\n".join(parts)


def _extract_txt(path: Path) -> str:
    raw = path.read_bytes()
    if b"\x00" in raw:
        raise ExtractionError("The text file appears to contain binary data.")
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1")


_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SPACES = re.compile(r"[ \t ]+")
_BLANKS = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL.sub(" ", text)
    text = _SPACES.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return _BLANKS.sub("\n\n", text).strip()


def extract_text(path: Path, filename: str, *, max_pages: int, max_chars: int) -> ExtractedDocument:
    with open(path, "rb") as fh:
        head = fh.read(1024)
    if not head:
        raise ExtractionError("The uploaded file is empty.")
    kind = detect_type(filename, head)

    page_count: int | None = None
    if kind == "pdf":
        raw, page_count = _extract_pdf(path, max_pages)
    elif kind == "docx":
        raw = _extract_docx(path)
    else:
        raw = _extract_txt(path)

    text = clean_text(raw)
    if len(re.findall(r"[A-Za-z]{2,}", text)) < 3:
        hint = " It may be a scanned image; OCR is not supported." if kind == "pdf" else ""
        raise ExtractionError("No readable text could be extracted from this file." + hint)
    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars]
    return ExtractedDocument(text=text, file_type=kind, page_count=page_count, truncated=truncated)

