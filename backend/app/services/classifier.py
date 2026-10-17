"""Loads the trained scikit-learn model and produces predictions with evidence-based explanations."""
from __future__ import annotations

import json
import threading
from pathlib import Path

import joblib
import numpy as np

from .categories import label_for, normalize_for_model
from .text_utils import split_sentences
from .uncertainty import assess


class ModelNotAvailable(RuntimeError):
    pass


def _display_term(feature: str) -> str:
    return feature.replace("numtoken", "#")


class DocumentClassifier:
    def __init__(self, model_path: Path, metrics_path: Path | None = None):
        if not model_path.exists():
            raise ModelNotAvailable(
                f"Model file not found at {model_path}. Train it with: python -m ml.train (from backend/).")
        bundle = joblib.load(model_path)
        self.pipeline = bundle["pipeline"]
        self.temperature = float(bundle.get("temperature", 1.0))
        self.version: str = bundle["model_version"]
        self.trained_at: str = bundle.get("trained_at", "")
        self.vectorizer = self.pipeline.named_steps["tfidf"]
        self.model = self.pipeline.named_steps["clf"]
        self.classes: list[str] = [str(c) for c in self.model.classes_]
        self.feature_names = [str(f) for f in self.vectorizer.get_feature_names_out()]
        self._analyzer = self.vectorizer.build_analyzer()
        self._tokenize = self.vectorizer.build_tokenizer()
        self._stop_words = self.vectorizer.get_stop_words() or frozenset()
        self.unigram_vocab = {f for f in self.vectorizer.vocabulary_ if " " not in f}
        self.metrics: dict = {}
        if metrics_path and metrics_path.exists():
            self.metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

    # ------------------------------------------------------------------ helpers
    def idf(self, term: str) -> float | None:
        idx = self.vectorizer.vocabulary_.get(term)
        return None if idx is None else float(self.vectorizer.idf_[idx])

    @property
    def max_idf(self) -> float:
        return float(self.vectorizer.idf_.max())

    def vocabulary_coverage(self, text: str) -> float:
        tokens = [t for t in self._tokenize(normalize_for_model(text))
                  if t not in self._stop_words and t != "numtoken"]
        if not tokens:
            return 0.0
        return sum(t in self.unigram_vocab for t in tokens) / len(tokens)

    def _scores(self, X) -> np.ndarray:
        logits = self.model.decision_function(X)[0] / self.temperature
        logits = logits - logits.max()
        e = np.exp(logits)
        return e / e.sum()

    # ------------------------------------------------------------------ main API
    def predict(self, text: str, word_count: int) -> dict:
        X = self.vectorizer.transform([text])
        scores = self._scores(X)
        order = np.argsort(scores)[::-1]
        top, second = int(order[0]), int(order[1])
        top_predictions = [
            {"category": self.classes[i], "label": label_for(self.classes[i]), "score": round(float(scores[i]), 4)}
            for i in order
        ]
        coverage = self.vocabulary_coverage(text)
        uncertainty = assess([float(scores[i]) for i in order], word_count, coverage)

        explanation = self._explain(X, text, top, second)
        explanation["vocabulary_coverage"] = round(coverage, 4)
        explanation["method"] = (
            "Linear model attribution: each term's contribution is its TF-IDF weight in this document "
            "multiplied by the model coefficient for the category. Evidence sentences are the sentences "
            "containing the strongest supporting terms.")
        return {
            "category": self.classes[top],
            "confidence": round(float(scores[top]), 4),
            "top_predictions": top_predictions,
            "is_uncertain": uncertainty["is_uncertain"],
            "uncertainty_reasons": uncertainty["reasons"],
            "explanation": explanation,
            "model_version": self.version,
        }

    def _explain(self, X, text: str, top: int, second: int) -> dict:
        row = X.tocsr()
        idx, vals = row.indices, row.data
        coef = self.model.coef_
        if len(idx) == 0:
            return {"supporting_terms": [], "opposing_terms": [], "evidence": [],
                    "runner_up": label_for(self.classes[second])}

        contrib_top = vals * coef[top, idx]
        contrib_vs_second = vals * (coef[top, idx] - coef[second, idx])

        def _terms(values: np.ndarray, positive: bool, limit: int) -> list[dict]:
            ordering = np.argsort(values)[::-1] if positive else np.argsort(values)
            out = []
            for j in ordering:
                if len(out) >= limit:
                    break
                v = float(values[j])
                if (positive and v <= 0) or (not positive and v >= 0):
                    break
                if all(tok == "numtoken" for tok in self.feature_names[idx[j]].split()):
                    continue  # a bare number placeholder is not a meaningful explanation for users
                out.append({"term": _display_term(self.feature_names[idx[j]]), "weight": round(v, 4)})
            return out

        supporting = _terms(contrib_top, True, 10)
        opposing = _terms(contrib_vs_second, False, 6)

        # Map features back to the sentences that contain them.
        term_weight = {self.feature_names[idx[j]]: float(contrib_top[j]) for j in range(len(idx))
                       if contrib_top[j] > 0}
        evidence = []
        for sentence in split_sentences(text):
            feats = set(self._analyzer(sentence))
            matched = sorted((f for f in feats if f in term_weight), key=lambda f: -term_weight[f])
            if not matched:
                continue
            score = sum(term_weight[f] for f in matched)
            evidence.append({
                "sentence": sentence if len(sentence) <= 300 else sentence[:297] + "...",
                "terms": [_display_term(f) for f in matched[:6]],
                "strength": round(score, 4),
            })
        evidence.sort(key=lambda e: -e["strength"])
        total = sum(e["strength"] for e in evidence) or 1.0
        for e in evidence:
            e["share"] = round(e["strength"] / total, 4)

        return {
            "supporting_terms": supporting,
            "opposing_terms": opposing,
            "runner_up": label_for(self.classes[second]),
            "evidence": evidence[:4],
        }


_lock = threading.Lock()
_instance: DocumentClassifier | None = None


def get_classifier() -> DocumentClassifier:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                from ..config import settings
                _instance = DocumentClassifier(settings.model_path, settings.metrics_path)
    return _instance
