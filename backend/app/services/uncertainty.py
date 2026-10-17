"""Documented uncertainty policy for classifier outputs.

A prediction is flagged "uncertain" (and shown to the user as such) when ANY rule fires.
The thresholds are fixed design choices, not values tuned to maximise a metric; their
effect (coverage, accuracy on confident predictions) is reported by ml/train.py.
"""
from __future__ import annotations

MIN_TOP_SCORE = 0.50       # top class score below this -> uncertain
MIN_MARGIN = 0.15          # top-1 minus top-2 score below this -> ambiguous
MIN_WORDS = 25             # too little text to classify reliably
MIN_VOCAB_COVERAGE = 0.30  # share of content words the model has seen during training

POLICY = {
    "min_top_score": MIN_TOP_SCORE,
    "min_margin": MIN_MARGIN,
    "min_words": MIN_WORDS,
    "min_vocabulary_coverage": MIN_VOCAB_COVERAGE,
    "description": (
        "A prediction is marked Uncertain if the top model score is below 0.50, if the gap between the "
        "top two categories is below 0.15, if the document has fewer than 25 words, or if fewer than 30% "
        "of its content words appear in the model's training vocabulary (a sign the document is outside "
        "the categories the model knows). Uncertain results still show the model's best guess, clearly "
        "labelled, so the user can judge it."
    ),
}


def assess_scores(sorted_scores: list[float]) -> dict:
    """Score-based rules only (used by training evaluation and at inference)."""
    reasons: list[str] = []
    top = float(sorted_scores[0])
    second = float(sorted_scores[1]) if len(sorted_scores) > 1 else 0.0
    if top < MIN_TOP_SCORE:
        reasons.append(f"Top model score {top:.0%} is below the {MIN_TOP_SCORE:.0%} threshold.")
    if top - second < MIN_MARGIN:
        reasons.append(f"The top two categories are within {top - second:.0%} of each other (ambiguous).")
    return {"is_uncertain": bool(reasons), "reasons": reasons}


def assess(sorted_scores: list[float], word_count: int, vocab_coverage: float) -> dict:
    result = assess_scores(sorted_scores)
    reasons = list(result["reasons"])
    if word_count < MIN_WORDS:
        reasons.append(f"Only {word_count} words of text were extracted (minimum {MIN_WORDS} for a reliable result).")
    if vocab_coverage < MIN_VOCAB_COVERAGE:
        reasons.append(
            f"Only {vocab_coverage:.0%} of the document's content words are known to the model; "
            "it may not belong to any supported category.")
    return {"is_uncertain": bool(reasons), "reasons": reasons}
