"""DocPredict FastAPI application."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__, database
from .config import settings
from .frontend import create_frontend_router
from .routers import analyses, auth, model_info, users
from .services.classifier import ModelNotAvailable, get_classifier

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("docpredict")


def _clean_stale_temp_files(temp_dir: Path) -> None:
    """Remove upload temp files left behind by a crashed process."""
    if temp_dir.exists():
        for leftover in temp_dir.glob("upload-*.bin"):
            leftover.unlink(missing_ok=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if database.engine is None:
        database.configure(settings.database_url)
    database.init_db()
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    _clean_stale_temp_files(settings.temp_dir)
    if settings.static_dir is not None and database.is_sqlite(settings.database_url):
        logger.warning("Production mode is using SQLite at %s. On hosts without a persistent disk "
                       "(e.g. Render's free plan) all data is lost on restart; set DOCPREDICT_DATABASE_URL "
                       "to a PostgreSQL database.", settings.database_url)
    if settings.secret_is_ephemeral:
        logger.warning("DOCPREDICT_SECRET_KEY is not set: using a temporary key. "
                       "Sessions will end whenever the server restarts. See backend/.env.example.")
    try:
        clf = get_classifier()
        logger.info("Loaded model %s (%d categories)", clf.version, len(clf.classes))
    except ModelNotAvailable as exc:
        logger.error("%s", exc)
    yield


app = FastAPI(
    title="DocPredict API",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


# Everything the app loads is same-origin; inline styles are needed by the charting library and
# Vite inlines small font subsets into the CSS as data: URLs.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
    "font-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; "
    "frame-ancestors 'none'"
)
_DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if not path.startswith(_DOCS_PATHS):  # Swagger UI loads its scripts from a CDN
        response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    if settings.enable_hsts:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if path.startswith("/assets/"):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"  # content-hashed names
    else:
        response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Return readable validation messages (without echoing submitted values such as passwords)."""
    errors = []
    for err in exc.errors():
        field = ".".join(str(p) for p in err.get("loc", []) if p not in ("body", "query", "path"))
        message = str(err.get("msg", "Invalid value")).removeprefix("Value error, ")
        errors.append({"field": field, "message": message})
    summary = errors[0]["message"] if errors else "Invalid request."
    return JSONResponse(status_code=422, content={"detail": summary, "errors": errors})


@app.get("/api/health", tags=["health"])
def health() -> dict:
    try:
        model_version = get_classifier().version
        model_ok = True
    except ModelNotAvailable:
        model_version, model_ok = None, False
    return {"status": "ok" if model_ok else "degraded", "version": __version__,
            "model_loaded": model_ok, "model_version": model_version}


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(analyses.router)
app.include_router(model_info.router)

# Single-service deployment: serve the built frontend. Must be registered last (catch-all route).
if settings.static_dir is not None:
    app.include_router(create_frontend_router(settings.static_dir))
