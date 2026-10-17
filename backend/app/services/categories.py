"""Document categories and the text normalisation shared by training and inference."""
from __future__ import annotations

import re

CATEGORIES: dict[str, str] = {
    "invoice": "Invoice",
    "contract": "Contract / Agreement",
    "resume": "Resume / CV",
    "medical_report": "Medical Report",
    "financial_report": "Financial Report",
    "research_paper": "Research Paper",
    "meeting_minutes": "Meeting Minutes",
    "legal_notice": "Legal Notice",
}

UNCERTAIN_LABEL = "Uncertain"

_NUMBER_RE = re.compile(r"\b\d[\d,.:/-]*\b")
_WS_RE = re.compile(r"\s+")


def label_for(category: str) -> str:
    return CATEGORIES.get(category, category.replace("_", " ").title())


def normalize_for_model(text: str) -> str:
    """Lower-case, collapse whitespace and replace digits with a placeholder token.

    Replacing numbers prevents the classifier from memorising specific amounts/dates
    and keeps training and inference consistent.
    """
    text = text.lower()
    text = _NUMBER_RE.sub(" numtoken ", text)
    return _WS_RE.sub(" ", text).strip()
