from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..config import settings
from ..models import User
from ..security import get_current_user
from ..services.categories import CATEGORIES
from ..services.classifier import ModelNotAvailable, get_classifier
from ..services.extraction import SUPPORTED_EXTENSIONS
from ..services.uncertainty import POLICY

router = APIRouter(prefix="/api/model", tags=["model"])


def _strip(evaluation: dict) -> dict:
    return {k: v for k, v in evaluation.items() if k != "errors"}


@router.get("")
def model_info(_: User = Depends(get_current_user)) -> dict:
    try:
        clf = get_classifier()
    except ModelNotAvailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    m = clf.metrics
    return {
        "model_version": clf.version,
        "trained_at": clf.trained_at,
        "algorithm": m.get("algorithm"),
        "hyperparameters": m.get("selected_hyperparameters"),
        "categories": [{"category": k, "label": v} for k, v in CATEGORIES.items()],
        "dataset": m.get("dataset"),
        "evaluation": {k: _strip(m[k]) for k in ("heldout_synthetic", "handwritten_dev", "handwritten_blind") if k in m},
        "uncertainty_policy": POLICY,
        "caveats": m.get("caveats", []),
        "supported_file_types": sorted(SUPPORTED_EXTENSIONS),
        "max_upload_mb": settings.max_upload_bytes // (1024 * 1024),
    }
