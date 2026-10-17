"""Train and evaluate the DocPredict document classifier.

Usage (from the backend directory):
    .venv\\Scripts\\python -m ml.train

Outputs:
    ml/artifacts/model.joblib   - fitted scikit-learn pipeline, score temperature (fixed at 1.0) and metadata
    ml/artifacts/metrics.json   - evaluation metrics

Evaluation sets:
    heldout_synthetic   25% stratified split of the generated corpus (same generator as training).
    handwritten_dev     24 hand-written texts. Used to diagnose the first model and to revise the generator
                        vocabulary, so its numbers are optimistic.
    handwritten_blind   16 hand-written texts never used for any fitting or tuning decision.

The deployed model is the one fitted on the training split only, so the reported
metrics describe exactly the model the API serves.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.categories import CATEGORIES, normalize_for_model  # noqa: E402
from app.services.uncertainty import POLICY, assess_scores  # noqa: E402
from ml.dataset import generate_corpus  # noqa: E402

ML_DIR = Path(__file__).resolve().parent
ARTIFACTS = ML_DIR / "artifacts"
DEV_SET = ML_DIR / "data" / "handwritten_dev.json"
BLIND_SET = ML_DIR / "data" / "handwritten_blind.json"
SEED = 42
MODEL_VERSION = "tfidf-logreg-1.0"


def build_pipeline(C: float = 4.0) -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            preprocessor=normalize_for_model,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.9,
            sublinear_tf=True,
            max_features=30000,
        )),
        ("clf", LogisticRegression(C=C, max_iter=3000, random_state=SEED)),
    ])


def softmax(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    z = logits / temperature
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def expected_calibration_error(probs: np.ndarray, correct: np.ndarray, n_bins: int = 10) -> dict:
    conf = probs.max(axis=1)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    bins = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (conf > lo) & (conf <= hi)
        if not mask.any():
            continue
        acc = float(correct[mask].mean())
        avg_conf = float(conf[mask].mean())
        ece += mask.mean() * abs(acc - avg_conf)
        bins.append({"range": [round(float(lo), 2), round(float(hi), 2)], "count": int(mask.sum()),
                     "accuracy": round(acc, 4), "mean_score": round(avg_conf, 4)})
    return {"ece": round(float(ece), 4), "bins": bins}


def evaluate(pipe: Pipeline, temperature: float, texts: list[str], labels: list[str]) -> dict:
    classes = list(pipe.classes_)
    logits = pipe.decision_function(texts)
    probs = softmax(logits, temperature)
    preds = [classes[i] for i in probs.argmax(axis=1)]
    correct = np.array([p == y for p, y in zip(preds, labels)])

    # Selective metrics under the documented uncertainty policy (score-based rules only).
    confident = np.array([not assess_scores(sorted(row, reverse=True))["is_uncertain"] for row in probs])
    coverage = float(confident.mean())
    selective_acc = float(correct[confident].mean()) if confident.any() else None

    report = classification_report(labels, preds, labels=classes, output_dict=True, zero_division=0)
    return {
        "n": len(labels),
        "accuracy": round(accuracy_score(labels, preds), 4),
        "macro_f1": round(f1_score(labels, preds, average="macro", zero_division=0), 4),
        "per_class": {c: {k: round(report[c][k], 4) for k in ("precision", "recall", "f1-score", "support")}
                      for c in classes},
        "confusion_matrix": {"labels": classes, "matrix": confusion_matrix(labels, preds, labels=classes).tolist()},
        "calibration": expected_calibration_error(probs, correct),
                "uncertainty_policy": {
            "coverage": round(coverage, 4),
            "accuracy_on_confident": None if selective_acc is None else round(selective_acc, 4),
            "flagged_uncertain": int((~confident).sum()),
        },
        "errors": [{"true": y, "pred": p, "text_start": t[:90]}
                   for t, y, p in zip(texts, labels, preds) if y != p][:15],
    }


def _load(path: Path) -> tuple[list[str], list[str]]:
    examples = json.loads(path.read_text(encoding="utf-8"))["examples"]
    return [e["text"] for e in examples], [e["label"] for e in examples]


def main() -> None:
    texts, labels = generate_corpus(n_per_class=200, seed=SEED)
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.25, stratify=labels, random_state=SEED)

    search = GridSearchCV(
        build_pipeline(),
        {"clf__C": [0.5, 1.0, 2.0, 4.0, 8.0, 16.0]},
        cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED),
        scoring="neg_log_loss",
        n_jobs=1,
    )
    search.fit(X_train, y_train)
    pipe: Pipeline = search.best_estimator_
    classes = list(pipe.classes_)

    dev_texts, dev_labels = _load(DEV_SET)
    blind_texts, blind_labels = _load(BLIND_SET)
    # Temperature scaling was evaluated and rejected: the dev set is perfectly separated by this model,
    # so the NLL-optimal temperature collapses towards 0 and would make every score ~100%.
    # Raw scores (T = 1) are served; they are under-confident on hand-written text (see calibration).
    temperature = 1.0

    metrics = {
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sklearn_version": sklearn.__version__,
        "algorithm": "TF-IDF (word 1-2 grams) + multinomial logistic regression (raw softmax scores)",
        "selected_hyperparameters": {"C": search.best_params_["clf__C"], "temperature": round(temperature, 4)},
        "cv_log_loss_on_train": round(float(-search.best_score_), 4),
        "dataset": {
            "type": "synthetic / illustrative",
            "description": ("Training documents are generated from hand-written sentence templates with randomised "
                            "values, shared boilerplate, cross-category noise and random word dropout "
                            "(ml/dataset.py, seed 42). They are not a sample of real-world documents."),
            "n_total": len(texts),
            "n_train": len(X_train),
            "n_test": len(X_test),
            "classes": {k: CATEGORIES[k] for k in classes},
        },
        "heldout_synthetic": evaluate(pipe, temperature, X_test, y_test),
        "handwritten_dev": evaluate(pipe, temperature, dev_texts, dev_labels),
        "handwritten_blind": evaluate(pipe, temperature, blind_texts, blind_labels),
        "uncertainty_policy": POLICY,
        "caveats": [
            "The held-out synthetic split comes from the same template generator as the training data, "
            "so it overstates accuracy on real documents.",
            "The hand-written development set influenced the generator's vocabulary, so its metrics are optimistic.",
            "The blind hand-written set is tiny (2 examples per category) and written by the same author as the "
            "generator; its accuracy has a very wide margin of error and is not an independent benchmark.",
            "Scores are raw logistic-regression softmax outputs. They are reported as model scores, not "
            "guaranteed probabilities. On the hand-written sets they are under-confident (observed accuracy was "
            "higher than the average score); on unfamiliar real documents they may be over-confident.",
            "Temperature scaling was tried and rejected because the development set is perfectly separated, "
            "which makes the fitted temperature degenerate.",
        ],
    }

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipe, "temperature": temperature, "model_version": MODEL_VERSION,
                 "trained_at": metrics["trained_at"]}, ARTIFACTS / "model.joblib")
    (ARTIFACTS / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(f"Selected C={search.best_params_['clf__C']}")
    for key in ("heldout_synthetic", "handwritten_dev", "handwritten_blind"):
        m = metrics[key]
        print(f"{key:18s}: acc {m['accuracy']:.3f}  macro-F1 {m['macro_f1']:.3f}  "
              f"ECE {m['calibration']['ece']:.3f}  "
              f"coverage {m['uncertainty_policy']['coverage']:.2f}  "
              f"acc@confident {m['uncertainty_policy']['accuracy_on_confident']}  (n={m['n']})")
    print(f"Saved model to {ARTIFACTS / 'model.joblib'}")


if __name__ == "__main__":
    main()
