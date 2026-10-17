"""Content-derived insights: extractive summary, keywords, pattern-based fields and rule-based priority.

Everything here is computed locally from the extracted text; nothing is sent to external services.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from .text_utils import STOP_WORDS, content_words, split_sentences, words

# ----------------------------------------------------------------------------- summary


def summarize(text: str, max_sentences: int | None = None) -> str:
    """Extractive summary: the highest-scoring sentences of the document, in original order.

    Sentence score = mean normalised frequency of its content words (frequency within this
    document), with a small bonus for early sentences. No text is generated.
    """
    sentences = split_sentences(text)
    candidates = [(i, s) for i, s in enumerate(sentences) if 5 <= len(words(s)) <= 80]
    if not candidates:
        candidates = [(i, s) for i, s in enumerate(sentences) if len(words(s)) >= 3]
    if not candidates:
        return ""

    freq = Counter(content_words(text))
    if not freq:
        return " ".join(s for _, s in candidates[:2])
    peak = max(freq.values())

    n_total = len(sentences)
    if max_sentences is None:
        max_sentences = 2 if n_total <= 6 else 3 if n_total <= 25 else 4

    scored = []
    for i, s in candidates:
        cw = content_words(s)
        if not cw:
            continue
        base = sum(freq[w] / peak for w in cw) / math.sqrt(len(cw))
        position_bonus = 0.15 * (1 - i / max(n_total, 1))
        scored.append((base + position_bonus, i, s))

    chosen = sorted(sorted(scored, reverse=True)[:max_sentences], key=lambda t: t[1])
    summary = " ".join(s if re.search(r"[.!?]$", s) else s + "." for _, _, s in chosen)
    return summary[:1200]


# ----------------------------------------------------------------------------- keywords


def extract_keywords(text: str, idf_lookup, default_idf: float, limit: int = 8) -> list[dict]:
    """Rank terms by in-document frequency x inverse document frequency.

    IDF comes from the classifier's training corpus; unseen terms receive the maximum IDF.
    """
    tokens = [w.lower() for w in words(text)]
    unigrams = Counter(t for t in tokens if t not in STOP_WORDS and len(t) > 2)
    bigrams = Counter(
        f"{a} {b}" for a, b in zip(tokens, tokens[1:])
        if a not in STOP_WORDS and b not in STOP_WORDS and len(a) > 2 and len(b) > 2
    )
    scores: dict[str, tuple[float, int]] = {}
    for term, count in unigrams.items():
        idf = idf_lookup(term) or default_idf
        scores[term] = ((1 + math.log(count)) * idf, count)
    for term, count in bigrams.items():
        if count < 2:
            continue
        idf = idf_lookup(term) or default_idf
        scores[term] = ((1 + math.log(count)) * idf * 1.3, count)

    ranked = sorted(scores.items(), key=lambda kv: -kv[1][0])
    result: list[dict] = []
    for term, (score, count) in ranked:
        # Skip unigrams already covered by a selected bigram.
        if any(term in r["term"].split() for r in result if " " in r["term"]):
            continue
        result.append({"term": term, "score": score, "count": count})
        if len(result) >= limit:
            break
    if result:
        top = result[0]["score"]
        for r in result:
            r["score"] = round(r["score"] / top, 3)
    return result


# ----------------------------------------------------------------------------- fields

_PATTERNS = {
    "emails": re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    "phone_numbers": re.compile(r"(?<![\w/])\+?\d{1,3}[\s.\-]?\(?\d{2,4}\)?[\s.\-]\d{3,4}[\s.\-]?\d{3,4}\b"),
    "dates": re.compile(
        r"\b(?:\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}-\d{2}-\d{2}|"
        r"\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?,?\s+\d{4}|"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})\b",
        re.IGNORECASE),
    "amounts": re.compile(
        r"(?:(?:[$€£₹]|\b(?:USD|EUR|GBP|INR|AUD|CAD)\s?)\s?\d[\d,]*(?:\.\d{1,2})?(?:\s?(?:million|billion|bn|m|k))?\b"
        r"|\b\d[\d,]*(?:\.\d{1,2})?\s?(?:USD|EUR|GBP|INR|dollars|euros|pounds)\b)",
        re.IGNORECASE),
    "percentages": re.compile(r"\b\d+(?:\.\d+)?\s?%"),
}
_REFERENCE_CODE = re.compile(r"\b(?:INV|PO|REF|ORD|ACC|CASE|CLAIM|TKT)-?\d{3,}[A-Z0-9\-]*\b")
_REFERENCE_LABELLED = re.compile(
    r"\b(?:invoice|order|reference|ref|account|case|claim|policy|receipt)\s*(?:no\.?|number|#)\s*[:#]?\s*"
    r"([A-Z0-9][A-Z0-9\-/]{2,})\b", re.IGNORECASE)

# "Label: value" lines worth surfacing when present.
_KEY_LABELS = [
    "invoice number", "invoice no", "invoice date", "due date", "total", "total due", "amount due", "balance due",
    "bill to", "customer", "payment terms", "patient", "date of birth", "diagnosis", "impression", "plan",
    "date of visit", "attendees", "present", "date", "agenda", "next meeting", "effective date", "term",
    "governing law", "parties", "education", "skills", "experience", "keywords", "abstract", "subject", "re",
]
_KEY_LINE = re.compile(r"^\s*(" + "|".join(re.escape(k) for k in sorted(_KEY_LABELS, key=len, reverse=True))
                       + r")\s*[:\-]\s*([^\n]{2,160}?)\s*$", re.IGNORECASE | re.MULTILINE)


def _unique(values, limit: int = 8) -> list[str]:
    seen, out = set(), []
    for v in values:
        v = " ".join(v.split()).strip(" .,;")
        key = v.lower()
        if v and key not in seen:
            seen.add(key)
            out.append(v)
        if len(out) >= limit:
            break
    return out


def extract_fields(text: str) -> dict:
    fields: dict[str, list] = {}
    for name, pattern in _PATTERNS.items():
        found = _unique(pattern.findall(text))
        if found:
            fields[name] = found
    references = _unique(_REFERENCE_CODE.findall(text) + _REFERENCE_LABELLED.findall(text))
    references = [r for r in references if any(c.isdigit() for c in r)]
    if references:
        fields["reference_numbers"] = references
    key_values = []
    seen_labels = set()
    for match in _KEY_LINE.finditer(text):
        label = match.group(1).strip().title()
        if label.lower() in seen_labels:
            continue
        seen_labels.add(label.lower())
        key_values.append({"label": label, "value": " ".join(match.group(2).split())[:160]})
        if len(key_values) >= 10:
            break
    if key_values:
        fields["key_values"] = key_values
    return fields


# ----------------------------------------------------------------------------- priority

_URGENT_TERMS = {
    "urgent": 2, "immediately": 2, "final notice": 3, "overdue": 2, "past due": 2, "legal action": 3,
    "legal proceedings": 3, "proceedings": 1, "court": 1, "deadline": 1, "asap": 2, "critical": 2,
    "emergency": 2, "abnormal": 1, "cease and desist": 3, "summons": 3, "breach": 1, "penalty": 1,
    "late fee": 1, "termination": 1, "action required": 2, "without further notice": 2, "referral": 1,
}
_CATEGORY_BASE = {"legal_notice": 2, "medical_report": 1, "invoice": 1, "contract": 1}
_WITHIN_DAYS = re.compile(r"within\s+(\d{1,3})\s+(?:business\s+|working\s+|calendar\s+)?days", re.IGNORECASE)


def assess_priority(text: str, category: str, is_uncertain: bool) -> tuple[str, list[str]]:
    """Heuristic attention level based on wording in the document. This is NOT a model output."""
    lowered = text.lower()
    score = 0
    reasons: list[str] = []

    hits = []
    for term, weight in _URGENT_TERMS.items():
        if re.search(r"\b" + re.escape(term) + r"\b", lowered):
            score += weight
            hits.append(term)
    if hits:
        reasons.append("Contains time-sensitive or escalation wording: " + ", ".join(f'"{h}"' for h in hits[:6]) + ".")

    deadlines = [int(d) for d in _WITHIN_DAYS.findall(text)]
    if deadlines:
        shortest = min(deadlines)
        if shortest <= 14:
            score += 2
            reasons.append(f"Mentions a short deadline (within {shortest} days).")
        else:
            score += 1
            reasons.append(f"Mentions a deadline (within {shortest} days).")

    if not is_uncertain and category in _CATEGORY_BASE:
        score += _CATEGORY_BASE[category]
        reasons.append("Document type usually requires follow-up action.")

    level = "high" if score >= 5 else "medium" if score >= 2 else "low"
    if not reasons:
        reasons.append("No urgency wording or deadlines were detected.")
    return level, reasons
