"""Sentence splitting and tokenisation helpers for extracted document text."""
from __future__ import annotations

import re

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

STOP_WORDS = frozenset(ENGLISH_STOP_WORDS) | {
    "shall", "hereby", "thereof", "page", "dear", "kind", "regards", "please", "thank", "thanks",
    "mr", "mrs", "ms", "dr", "etc", "per", "also", "may", "will", "can", "one", "two",
}

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[\"'(\[]?[A-Z0-9])")
_ABBREV = re.compile(r"\b(?:Mr|Mrs|Ms|Dr|Prof|No|Inc|Ltd|Co|vs|etc|e\.g|i\.e|St|approx)\.$", re.IGNORECASE)
_WORD = re.compile(r"[A-Za-z][A-Za-z']*(?:-[A-Za-z]+)*")


def _merge_wrapped_lines(paragraph: str) -> list[str]:
    """Join lines broken by PDF wrapping; keep headings and list items as separate units."""
    units: list[str] = []
    for line in paragraph.split("\n"):
        line = line.strip()
        if not line:
            continue
        if units and not re.search(r"[.!?:;]$", units[-1]) and line[:1].islower():
            units[-1] = f"{units[-1]} {line}"
        else:
            units.append(line)
    return units


def split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    for paragraph in re.split(r"\n\s*\n", text):
        for unit in _merge_wrapped_lines(paragraph):
            pieces = _SENTENCE_END.split(unit)
            buffer = ""
            for piece in pieces:
                buffer = f"{buffer} {piece}".strip() if buffer else piece
                if _ABBREV.search(buffer):
                    continue
                sentences.append(buffer)
                buffer = ""
            if buffer:
                sentences.append(buffer)
    return [s.strip() for s in sentences if len(s.strip()) > 1]


def words(text: str) -> list[str]:
    return _WORD.findall(text)


def content_words(text: str) -> list[str]:
    return [w.lower() for w in words(text) if w.lower() not in STOP_WORDS and len(w) > 2]
