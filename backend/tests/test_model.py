from __future__ import annotations

import json

import pytest

from app.config import settings
from app.services.analyzer import analyze_text
from app.services.classifier import get_classifier
from app.services.insights import assess_priority, extract_fields, summarize

from . import samples


@pytest.mark.parametrize("expected,text", list(samples.SAMPLES.items()))
def test_classifies_sample_documents(expected, text):
    pred = get_classifier().predict(text, len(text.split()))
    assert pred["category"] == expected
    assert not pred["is_uncertain"], pred["uncertainty_reasons"]
    scores = [p["score"] for p in pred["top_predictions"]]
    assert scores == sorted(scores, reverse=True)
    assert abs(sum(scores) - 1.0) < 0.01


def test_prediction_is_deterministic():
    a = get_classifier().predict(samples.CONTRACT_TEXT, 100)
    b = get_classifier().predict(samples.CONTRACT_TEXT, 100)
    assert a == b


def test_out_of_scope_document_flagged_uncertain():
    result = analyze_text(samples.OUT_OF_SCOPE_TEXT)
    pred = result["prediction"]
    assert pred["is_uncertain"]
    assert any("known to the model" in r for r in pred["uncertainty_reasons"])


def test_very_short_text_flagged_uncertain():
    pred = analyze_text("Invoice total due now.")["prediction"]
    assert pred["is_uncertain"]
    assert any("words of text" in r for r in pred["uncertainty_reasons"])


def test_ambiguous_mixed_document_flagged():
    mixed = samples.INVOICE_TEXT + "\n" + samples.RESUME_TEXT
    pred = get_classifier().predict(mixed, 200)
    top2 = [p["category"] for p in pred["top_predictions"][:2]]
    assert set(top2) == {"invoice", "resume"}
    assert pred["is_uncertain"]


def test_explanation_evidence_comes_from_document():
    pred = get_classifier().predict(samples.MEDICAL_TEXT, 120)
    expl = pred["explanation"]
    assert expl["supporting_terms"], "expected supporting terms"
    assert all(t["weight"] > 0 for t in expl["supporting_terms"])
    assert expl["evidence"]
    flat = " ".join(samples.MEDICAL_TEXT.split())
    for ev in expl["evidence"]:
        assert " ".join(ev["sentence"].split())[:40] in flat
        assert ev["terms"]
    assert 0 < expl["vocabulary_coverage"] <= 1


def test_classification_uses_content_not_filename():
    # The classifier only receives text; identical text always gives the identical result.
    r1 = analyze_text(samples.LEGAL_TEXT)["prediction"]
    r2 = analyze_text(samples.LEGAL_TEXT)["prediction"]
    assert r1["category"] == r2["category"] == "legal_notice"


def test_summary_is_extractive_and_shorter_than_text():
    summary = summarize(samples.CONTRACT_TEXT)
    assert summary and len(summary) < len(samples.CONTRACT_TEXT)
    flat = " ".join(samples.CONTRACT_TEXT.split())
    for sentence in summary.split(". "):
        assert sentence.rstrip(".")[:30] in flat


def test_keywords_and_fields():
    result = analyze_text(samples.INVOICE_TEXT)
    terms = [k["term"] for k in result["keywords"]]
    assert 3 <= len(terms) <= 8
    assert any(t in terms for t in ("invoice", "payment", "licence", "harbor"))
    fields = result["extracted_fields"]
    assert "$4,536.00" in fields["amounts"]
    assert "INV-48213" in fields["reference_numbers"]
    assert "accounts@northwind.example" in fields["emails"]
    assert {"label": "Invoice Number", "value": "INV-48213"} in fields["key_values"]


def test_fields_empty_when_absent():
    assert extract_fields("A plain sentence without any structured data at all.") == {}


def test_priority_is_rule_based_and_separate_from_confidence():
    high, reasons = assess_priority(samples.LEGAL_TEXT, "legal_notice", False)
    assert high == "high" and any("deadline" in r for r in reasons)
    low, reasons = assess_priority(samples.RESUME_TEXT, "resume", False)
    assert low == "low"
    # Category does not raise priority when the classification is uncertain.
    level_certain, _ = assess_priority("Please review.", "legal_notice", False)
    level_uncertain, _ = assess_priority("Please review.", "legal_notice", True)
    assert level_certain == "medium" and level_uncertain == "low"


def test_metrics_file_reports_real_evaluation():
    metrics = json.loads(settings.metrics_path.read_text(encoding="utf-8"))
    assert metrics["dataset"]["type"] == "synthetic / illustrative"
    for key in ("heldout_synthetic", "handwritten_dev", "handwritten_blind"):
        assert 0 <= metrics[key]["accuracy"] <= 1
        assert metrics[key]["n"] > 0
    assert metrics["heldout_synthetic"]["n"] == metrics["dataset"]["n_test"]
