"""Application settings loaded from environment variables (and an optional backend/.env file)."""
from __future__ import annotations

import logging
import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

logger = logging.getLogger("docpredict")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be an integer, got {raw!r}") from exc


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    if raw.strip().lower() in ("1", "true", "yes", "on"):
        return True
    if raw.strip().lower() in ("0", "false", "no", "off"):
        return False
    raise RuntimeError(f"Environment variable {name} must be true or false, got {raw!r}")


def _resolve_secret() -> tuple[str, bool]:
    secret = os.getenv("DOCPREDICT_SECRET_KEY", "").strip()
    if secret:
        if len(secret) < 32:
            raise RuntimeError("DOCPREDICT_SECRET_KEY must be at least 32 characters long.")
        return secret, False
    # No secret configured: use an ephemeral one so nothing insecure is hard-coded.
    # Tokens are invalidated whenever the process restarts.
    return secrets.token_urlsafe(48), True


@dataclass(frozen=True)
class Settings:
    secret_key: str
    secret_is_ephemeral: bool
    database_url: str
    temp_dir: Path
    model_path: Path
    metrics_path: Path
    max_upload_bytes: int
    max_pdf_pages: int
    max_text_chars: int
    token_expire_minutes: int
    cors_origins: list[str] = field(default_factory=list)
    static_dir: Path | None = None   # built frontend (frontend/dist) to serve from the API server
    enable_docs: bool = True         # interactive API docs at /docs
    enable_hsts: bool = False        # only behind HTTPS (e.g. on Render)
    jwt_algorithm: str = "HS256"


def load_settings() -> Settings:
    secret, ephemeral = _resolve_secret()
    data_dir = Path(os.getenv("DOCPREDICT_DATA_DIR", str(BACKEND_DIR / "data")))
    database_url = os.getenv("DOCPREDICT_DATABASE_URL", f"sqlite:///{(data_dir / 'docpredict.db').as_posix()}")
    temp_dir = Path(os.getenv("DOCPREDICT_TEMP_DIR", str(data_dir / "tmp")))
    artifacts = BACKEND_DIR / "ml" / "artifacts"
    origins = os.getenv("DOCPREDICT_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return Settings(
        secret_key=secret,
        secret_is_ephemeral=ephemeral,
        database_url=database_url,
        temp_dir=temp_dir,
        model_path=Path(os.getenv("DOCPREDICT_MODEL_PATH", str(artifacts / "model.joblib"))),
        metrics_path=Path(os.getenv("DOCPREDICT_METRICS_PATH", str(artifacts / "metrics.json"))),
        max_upload_bytes=_env_int("DOCPREDICT_MAX_UPLOAD_MB", 10) * 1024 * 1024,
        max_pdf_pages=_env_int("DOCPREDICT_MAX_PDF_PAGES", 200),
        max_text_chars=_env_int("DOCPREDICT_MAX_TEXT_CHARS", 200_000),
        token_expire_minutes=_env_int("DOCPREDICT_TOKEN_EXPIRE_MINUTES", 120),
        cors_origins=[o.strip() for o in origins.split(",") if o.strip()],
        static_dir=Path(os.environ["DOCPREDICT_STATIC_DIR"]) if os.getenv("DOCPREDICT_STATIC_DIR") else None,
        enable_docs=_env_bool("DOCPREDICT_ENABLE_DOCS", True),
        enable_hsts=_env_bool("DOCPREDICT_ENABLE_HSTS", False),
    )


settings = load_settings()
