"""Serves the built React app (frontend/dist) from the API server for single-service deployments.

Real files (hashed assets, favicon, theme-init.js) are returned directly; every other non-API
path returns index.html so client-side routes such as /history work on reload.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse


def create_frontend_router(static_dir: Path) -> APIRouter:
    root = static_dir.resolve()
    index = root / "index.html"
    if not index.is_file():
        raise RuntimeError(f"Built frontend not found: {index} (run `npm run build` in frontend/)")

    router = APIRouter(include_in_schema=False)

    @router.api_route("/{full_path:path}", methods=["GET", "HEAD"])
    def serve(full_path: str) -> FileResponse:
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(404, "Not found.")
        if full_path:
            candidate = (root / full_path).resolve()
            # Only files inside the build folder; ".." tricks resolve outside and fall through.
            if candidate.is_file() and root in candidate.parents:
                return FileResponse(candidate)
            if "." in full_path.rsplit("/", 1)[-1]:
                raise HTTPException(404, "Not found.")  # missing asset: don't answer with HTML
        return FileResponse(index)

    return router
