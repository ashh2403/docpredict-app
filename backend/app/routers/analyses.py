from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import String, cast, delete, func, or_, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Analysis, User
from ..schemas import AnalysisDetail, AnalysisPage, AnalysisSummary, AnalysisUpdate, MessageResponse
from ..security import get_current_user
from ..services.analyzer import UploadTooLarge, analyze_upload
from ..services.categories import CATEGORIES, label_for
from ..services.classifier import ModelNotAvailable
from ..services.extraction import ExtractionError

router = APIRouter(prefix="/api/analyses", tags=["analyses"])


def _summary(a: Analysis) -> AnalysisSummary:
    return AnalysisSummary.model_validate(_base(a))


def _base(a: Analysis) -> dict:
    return {
        "id": a.id, "filename": a.filename, "file_type": a.file_type, "file_size": a.file_size,
        "word_count": a.word_count, "category": a.category, "category_label": label_for(a.category),
        "confidence": a.confidence, "is_uncertain": a.is_uncertain, "priority": a.priority,
        "bookmarked": a.bookmarked, "summary": a.summary, "keywords": a.keywords, "created_at": a.created_at,
    }


def _detail(a: Analysis) -> AnalysisDetail:
    return AnalysisDetail.model_validate({
        **_base(a),
        "page_count": a.page_count, "char_count": a.char_count, "uncertainty_reasons": a.uncertainty_reasons,
        "top_predictions": a.top_predictions, "explanation": a.explanation,
        "extracted_fields": a.extracted_fields, "priority_reasons": a.priority_reasons,
        "model_version": a.model_version, "processing_ms": a.processing_ms,
    })


def _owned(db: Session, user: User, analysis_id: int) -> Analysis:
    analysis = db.scalar(select(Analysis).where(Analysis.id == analysis_id, Analysis.user_id == user.id))
    if analysis is None:
        # Same response whether the record does not exist or belongs to someone else.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis not found.")
    return analysis


@router.post("", response_model=AnalysisDetail, status_code=status.HTTP_201_CREATED)
async def create_analysis(file: UploadFile = File(...), user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)) -> AnalysisDetail:
    try:
        result = await analyze_upload(file)
    except UploadTooLarge as exc:
        limit_mb = settings.max_upload_bytes // (1024 * 1024)
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            f"File is too large. The maximum size is {limit_mb} MB.") from exc
    except ExtractionError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    except ModelNotAvailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "The classification model is not available. Ask the administrator to train it.") from exc
    finally:
        await file.close()

    pred = result.prediction
    reasons = list(pred["uncertainty_reasons"])
    if result.truncated:
        reasons.append(f"Only the first {settings.max_text_chars:,} characters were analysed.")
    analysis = Analysis(
        user_id=user.id,
        filename=result.filename,
        file_type=result.file_type,
        file_size=result.file_size,
        page_count=result.page_count,
        word_count=result.word_count,
        char_count=result.char_count,
        category=pred["category"],
        confidence=pred["confidence"],
        is_uncertain=pred["is_uncertain"],
        uncertainty_reasons=reasons,
        top_predictions=pred["top_predictions"],
        explanation=pred["explanation"],
        model_version=pred["model_version"],
        summary=result.summary,
        keywords=result.keywords,
        extracted_fields=result.extracted_fields,
        priority=result.priority,
        priority_reasons=result.priority_reasons,
        processing_ms=result.processing_ms,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return _detail(analysis)


@router.get("", response_model=AnalysisPage)
def list_analyses(
    q: str | None = Query(default=None, max_length=100),
    category: str | None = Query(default=None, max_length=40),
    priority: Literal["low", "medium", "high"] | None = None,
    bookmarked: bool | None = None,
    uncertain: bool | None = None,
    sort: Literal["newest", "oldest", "confidence", "name"] = "newest",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AnalysisPage:
    conditions = [Analysis.user_id == user.id]
    if q and q.strip():
        term = q.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        like = f"%{term}%"
        conditions.append(or_(
            func.lower(Analysis.filename).like(like, escape="\\"),
            func.lower(Analysis.summary).like(like, escape="\\"),
            func.lower(Analysis.category).like(like, escape="\\"),
            func.lower(cast(Analysis.keywords, String)).like(like, escape="\\"),
        ))
    if category:
        if category not in CATEGORIES:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown category.")
        conditions.append(Analysis.category == category)
    if priority:
        conditions.append(Analysis.priority == priority)
    if bookmarked is not None:
        conditions.append(Analysis.bookmarked == bookmarked)
    if uncertain is not None:
        conditions.append(Analysis.is_uncertain == uncertain)

    order = {
        "newest": (Analysis.created_at.desc(), Analysis.id.desc()),
        "oldest": (Analysis.created_at.asc(), Analysis.id.asc()),
        "confidence": (Analysis.confidence.desc(), Analysis.id.desc()),
        "name": (func.lower(Analysis.filename).asc(), Analysis.id.asc()),
    }[sort]

    total = db.scalar(select(func.count()).select_from(Analysis).where(*conditions)) or 0
    rows = db.scalars(select(Analysis).where(*conditions).order_by(*order)
                      .offset((page - 1) * page_size).limit(page_size)).all()
    return AnalysisPage(items=[_summary(a) for a in rows], total=total, page=page, page_size=page_size)


@router.get("/stats")
def stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    base = select(Analysis).where(Analysis.user_id == user.id)
    rows = db.scalars(base).all()
    by_category: dict[str, int] = {}
    by_priority = {"low": 0, "medium": 0, "high": 0}
    for a in rows:
        by_category[a.category] = by_category.get(a.category, 0) + 1
        by_priority[a.priority] = by_priority.get(a.priority, 0) + 1

    today = datetime.now(timezone.utc).date()
    days = [today - timedelta(days=i) for i in range(13, -1, -1)]
    per_day = {d.isoformat(): 0 for d in days}
    for a in rows:
        key = a.created_at.astimezone(timezone.utc).date().isoformat()
        if key in per_day:
            per_day[key] += 1

    total = len(rows)
    return {
        "total": total,
        "bookmarked": sum(a.bookmarked for a in rows),
        "uncertain": sum(a.is_uncertain for a in rows),
        "average_confidence": round(sum(a.confidence for a in rows) / total, 4) if total else None,
        "by_category": [{"category": c, "label": label_for(c), "count": n}
                        for c, n in sorted(by_category.items(), key=lambda kv: -kv[1])],
        "by_priority": by_priority,
        "per_day": [{"date": d, "count": n} for d, n in per_day.items()],
    }


@router.get("/{analysis_id}", response_model=AnalysisDetail)
def get_analysis(analysis_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _detail(_owned(db, user, analysis_id))


@router.patch("/{analysis_id}", response_model=AnalysisDetail)
def update_analysis(analysis_id: int, body: AnalysisUpdate, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    analysis = _owned(db, user, analysis_id)
    analysis.bookmarked = body.bookmarked
    db.commit()
    db.refresh(analysis)
    return _detail(analysis)


@router.delete("/{analysis_id}", response_model=MessageResponse)
def delete_analysis(analysis_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_owned(db, user, analysis_id))
    db.commit()
    return MessageResponse(detail="Analysis deleted.")


@router.delete("", response_model=MessageResponse)
def delete_all_analyses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    result = db.execute(delete(Analysis).where(Analysis.user_id == user.id))
    db.commit()
    return MessageResponse(detail=f"Deleted {result.rowcount} saved analyses.")
