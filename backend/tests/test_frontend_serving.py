from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.frontend import create_frontend_router
from app.main import CONTENT_SECURITY_POLICY


@pytest.fixture()
def spa(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>DocPredict</title>", encoding="utf-8")
    (dist / "assets" / "index-abc123.js").write_text("console.log(1)", encoding="utf-8")
    (dist / "theme-init.js").write_text("// theme", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("outside the build folder", encoding="utf-8")
    app = FastAPI()

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    app.include_router(create_frontend_router(dist))
    return TestClient(app)


def test_serves_index_for_root_and_client_routes(spa):
    for path in ("/", "/history", "/analyses/42", "/settings"):
        res = spa.get(path)
        assert res.status_code == 200 and "<title>DocPredict</title>" in res.text, path


def test_serves_real_files(spa):
    assert spa.get("/assets/index-abc123.js").text == "console.log(1)"
    assert spa.get("/theme-init.js").text == "// theme"


def test_api_routes_win_and_unknown_api_paths_are_404(spa):
    assert spa.get("/api/ping").json() == {"ok": True}
    assert spa.get("/api/does-not-exist").status_code == 404
    assert spa.get("/api").status_code == 404


def test_head_requests_supported(spa):
    assert spa.head("/").status_code == 200
    assert spa.head("/assets/index-abc123.js").status_code == 200


def test_missing_asset_is_404_not_html(spa):
    assert spa.get("/assets/missing-file.js").status_code == 404


def test_path_traversal_cannot_escape_build_folder(spa):
    for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/assets/..%2f..%2fsecret.txt"):
        res = spa.get(path)
        assert "outside the build folder" not in res.text, path


def test_missing_build_is_reported(tmp_path):
    with pytest.raises(RuntimeError, match="npm run build"):
        create_frontend_router(tmp_path / "nope")


def test_security_and_cache_headers_on_api(client):
    res = client.get("/api/health")
    assert res.headers["Content-Security-Policy"] == CONTENT_SECURITY_POLICY
    assert "script-src 'self'" in CONTENT_SECURITY_POLICY and "unsafe-eval" not in CONTENT_SECURITY_POLICY
    assert res.headers["Cache-Control"] == "no-store"
    assert "Strict-Transport-Security" not in res.headers  # HSTS only when enabled for HTTPS hosts
