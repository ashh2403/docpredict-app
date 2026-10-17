from __future__ import annotations

from pathlib import Path

import pytest

from app.services.extraction import ExtractionError, extract_text, safe_display_name
from app.services.text_utils import split_sentences

from . import samples

LIMITS = {"max_pages": 50, "max_chars": 200_000}


def _write(tmp_path: Path, data: bytes, name: str = "file.bin") -> Path:
    path = tmp_path / name
    path.write_bytes(data)
    return path


def test_pdf_extraction(tmp_path):
    doc = extract_text(_write(tmp_path, samples.make_pdf(samples.INVOICE_TEXT)), "invoice.pdf", **LIMITS)
    assert doc.file_type == "pdf" and doc.page_count == 1
    assert "INV-48213" in doc.text and "Harbor Dental Clinic" in doc.text


def test_docx_extraction_includes_tables(tmp_path):
    doc = extract_text(_write(tmp_path, samples.make_docx(samples.CONTRACT_TEXT)), "contract.docx", **LIMITS)
    assert doc.file_type == "docx" and doc.page_count is None
    assert "Bluepeak Software" in doc.text
    assert "Prepared by | Document control" in doc.text


def test_txt_extraction_handles_bom_and_cp1252(tmp_path):
    utf8 = extract_text(_write(tmp_path, b"\xef\xbb\xbfCaf\xc3\xa9 menu with several words here", "a.txt"),
                        "a.txt", **LIMITS)
    assert utf8.text.startswith("Café")
    legacy = extract_text(_write(tmp_path, "Résumé text with café words".encode("cp1252"), "b.txt"),
                          "b.txt", **LIMITS)
    assert "Résumé" in legacy.text


@pytest.mark.parametrize("name,data,message", [
    ("fake.pdf", b"just some text, not a pdf at all", "not a valid PDF"),
    ("fake.docx", b"%PDF-1.4 something", "not a valid Word"),
    ("binary.txt", b"MZ\x00\x00\x90binary", "binary"),
    ("image.png", b"\x89PNG\r\n\x1a\n", "Unsupported file type"),
    ("script.exe", b"MZ", "Unsupported file type"),
    ("noext", b"hello", "Unsupported file type"),
    ("empty.txt", b"", "empty"),
])
def test_rejects_invalid_files(tmp_path, name, data, message):
    with pytest.raises(ExtractionError, match=message):
        extract_text(_write(tmp_path, data, "upload.bin"), name, **LIMITS)


def test_rejects_encrypted_pdf(tmp_path):
    with pytest.raises(ExtractionError, match="Password-protected"):
        extract_text(_write(tmp_path, samples.make_encrypted_pdf(samples.INVOICE_TEXT)), "x.pdf", **LIMITS)


def test_rejects_image_only_pdf(tmp_path):
    with pytest.raises(ExtractionError, match="OCR is not supported"):
        extract_text(_write(tmp_path, samples.make_image_only_pdf()), "scan.pdf", **LIMITS)


def test_rejects_truncated_pdf(tmp_path):
    data = samples.make_pdf(samples.INVOICE_TEXT)
    with pytest.raises(ExtractionError):
        extract_text(_write(tmp_path, data[: len(data) // 3]), "broken.pdf", **LIMITS)


def test_rejects_zip_that_is_not_docx(tmp_path):
    with pytest.raises(ExtractionError, match="not a valid Word"):
        extract_text(_write(tmp_path, samples.make_corrupt_docx()), "x.docx", **LIMITS)


def test_rejects_docx_zip_bomb(tmp_path):
    with pytest.raises(ExtractionError, match="compression ratio|too large"):
        extract_text(_write(tmp_path, samples.make_docx_bomb()), "bomb.docx", **LIMITS)


def test_page_limit(tmp_path):
    long_text = "\n".join(["Invoice line item with several words for testing."] * 400)
    with pytest.raises(ExtractionError, match="limit is 2"):
        extract_text(_write(tmp_path, samples.make_pdf(long_text)), "long.pdf", max_pages=2, max_chars=10_000)


def test_text_truncated_to_limit(tmp_path):
    doc = extract_text(_write(tmp_path, ("word " * 5000).encode()), "big.txt", max_pages=5, max_chars=1000)
    assert doc.truncated and len(doc.text) == 1000


@pytest.mark.parametrize("raw,expected", [
    ("../../etc/passwd", "passwd"),
    ("C:\\Windows\\System32\\evil.pdf", "evil.pdf"),
    ("<script>alert(1)<script>.txt", "_script_alert(1)_script_.txt"),
    ("<script>alert(1)</script>.txt", "script_.txt"),  # "/" is a path separator
    ("", "document"),
    ("...", "document"),
    ("report final (v2).docx", "report final (v2).docx"),
])
def test_safe_display_name(raw, expected):
    assert safe_display_name(raw) == expected


def test_safe_display_name_limits_length():
    name = safe_display_name("a" * 300 + ".pdf")
    assert len(name) <= 120 and name.endswith(".pdf")


def test_sentence_splitting_merges_wrapped_lines():
    text = "This sentence was wrapped\nacross two lines. Dr. Smith signed it.\nHEADING\nNext item."
    assert split_sentences(text) == ["This sentence was wrapped across two lines.", "Dr. Smith signed it.",
                                     "HEADING", "Next item."]
