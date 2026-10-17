from __future__ import annotations

import dataclasses
import sqlite3

import pytest

from app.routers import analyses as analyses_router
from app.services import analyzer

from . import samples


def upload(client, headers, name: str, data: bytes, content_type: str = "application/octet-stream"):
    return client.post("/api/analyses", headers=headers, files={"file": (name, data, content_type)})


def _leftover_uploads(temp_dir):
    return list(temp_dir.glob("upload-*")) if temp_dir.exists() else []


@pytest.mark.parametrize("name,builder,text,expected", [
    ("invoice.pdf", samples.make_pdf, samples.INVOICE_TEXT, "invoice"),
    ("agreement.docx", samples.make_docx, samples.CONTRACT_TEXT, "contract"),
    ("notes.txt", samples.make_txt, samples.MEDICAL_TEXT, "medical_report"),
])
def test_upload_analyse_and_retrieve(client, alice, temp_dir, name, builder, text, expected):
    res = upload(client, alice["headers"], name, builder(text))
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["category"] == expected
    assert body["filename"] == name
    assert body["file_type"] == name.rsplit(".", 1)[1]
    assert 0 < body["confidence"] <= 1
    assert body["summary"] and body["keywords"]
    assert body["explanation"]["evidence"]
    assert body["priority"] in {"low", "medium", "high"} and body["priority_reasons"]
    assert body["word_count"] > 25
    assert body["created_at"].endswith(("Z", "+00:00"))

    fetched = client.get(f"/api/analyses/{body['id']}", headers=alice["headers"])
    assert fetched.status_code == 200 and fetched.json() == body
    assert _leftover_uploads(temp_dir) == []


def test_upload_failure_cleans_temp_and_saves_nothing(client, alice, temp_dir, db_path):
    res = upload(client, alice["headers"], "scan.pdf", samples.make_image_only_pdf())
    assert res.status_code == 422 and "OCR" in res.json()["detail"]
    res = upload(client, alice["headers"], "fake.pdf", b"not a pdf")
    assert res.status_code == 422
    assert _leftover_uploads(temp_dir) == []
    assert sqlite3.connect(db_path).execute("SELECT COUNT(*) FROM analyses").fetchone()[0] == 0


def test_upload_validation_errors(client, alice):
    assert client.post("/api/analyses", headers=alice["headers"]).status_code == 422  # no file
    res = upload(client, alice["headers"], "malware.exe", b"MZ\x90\x00")
    assert res.status_code == 422 and "Unsupported" in res.json()["detail"]
    res = upload(client, alice["headers"], "empty.txt", b"")
    assert res.status_code == 422 and "empty" in res.json()["detail"]


def test_upload_too_large(client, alice, temp_dir, monkeypatch):
    small = dataclasses.replace(analyzer.settings, max_upload_bytes=1024)
    monkeypatch.setattr(analyzer, "settings", small)
    monkeypatch.setattr(analyses_router, "settings", small)
    res = upload(client, alice["headers"], "big.txt", b"word " * 1000)
    assert res.status_code == 413
    assert _leftover_uploads(temp_dir) == []


def test_upload_requires_auth(client):
    assert upload(client, {}, "a.txt", samples.make_txt(samples.INVOICE_TEXT)).status_code == 401


def test_filename_is_sanitised(client, alice):
    res = upload(client, alice["headers"], r"..\..\<b>evil<b>.txt", samples.make_txt(samples.INVOICE_TEXT))
    assert res.status_code == 201
    assert res.json()["filename"] == "_b_evil_b_.txt"


def test_full_text_and_file_are_not_persisted(client, alice, db_path, temp_dir):
    long_text = samples.CONTRACT_TEXT + "\n" + "\n".join(
        f"Clause {i}. The parties agree that obligation number {i} continues for the agreed term." for i in range(150))
    res = upload(client, alice["headers"], "long.txt", samples.make_txt(long_text))
    assert res.status_code == 201
    con = sqlite3.connect(db_path)
    columns = [r[1] for r in con.execute("PRAGMA table_info(analyses)")]
    assert not any(c in columns for c in ("text", "content", "full_text", "file_data"))
    row = con.execute("SELECT * FROM analyses").fetchone()
    stored = " ".join(str(v) for v in row)
    assert long_text not in stored
    assert len(stored) < len(long_text) / 2
    assert _leftover_uploads(temp_dir) == []


def _seed(client, headers):
    ids = {}
    for name, builder, text in [
        ("acme-invoice.pdf", samples.make_pdf, samples.INVOICE_TEXT),
        ("consulting.docx", samples.make_docx, samples.CONTRACT_TEXT),
        ("cv-aisha.txt", samples.make_txt, samples.RESUME_TEXT),
        ("final-notice.txt", samples.make_txt, samples.LEGAL_TEXT),
    ]:
        res = upload(client, headers, name, builder(text))
        assert res.status_code == 201, res.text
        ids[name] = res.json()["id"]
    return ids


def test_history_search_filter_sort_paginate(client, alice):
    ids = _seed(client, alice["headers"])
    h = alice["headers"]

    all_items = client.get("/api/analyses", headers=h).json()
    assert all_items["total"] == 4
    assert [i["id"] for i in all_items["items"]] == sorted(ids.values(), reverse=True)  # newest first

    by_name = client.get("/api/analyses", headers=h, params={"q": "AISHA"}).json()
    assert [i["filename"] for i in by_name["items"]] == ["cv-aisha.txt"]

    invoice = client.get(f"/api/analyses/{ids['acme-invoice.pdf']}", headers=h).json()
    assert "harbor" in invoice["summary"].lower() or "harbor" in str(invoice["keywords"]).lower()
    by_content = client.get("/api/analyses", headers=h, params={"q": "harbor"}).json()
    assert [i["filename"] for i in by_content["items"]] == ["acme-invoice.pdf"]

    wildcard = client.get("/api/analyses", headers=h, params={"q": "%"}).json()
    assert wildcard["total"] == 0  # LIKE wildcards are escaped

    by_cat = client.get("/api/analyses", headers=h, params={"category": "contract"}).json()
    assert [i["filename"] for i in by_cat["items"]] == ["consulting.docx"]

    high = client.get("/api/analyses", headers=h, params={"priority": "high"}).json()
    assert "final-notice.txt" in [i["filename"] for i in high["items"]]

    by_name_sort = client.get("/api/analyses", headers=h, params={"sort": "name"}).json()
    names = [i["filename"] for i in by_name_sort["items"]]
    assert names == sorted(names, key=str.lower)

    page = client.get("/api/analyses", headers=h, params={"page": 2, "page_size": 3}).json()
    assert page["total"] == 4 and len(page["items"]) == 1

    assert client.get("/api/analyses", headers=h, params={"category": "bogus"}).status_code == 422
    assert client.get("/api/analyses", headers=h, params={"sort": "bogus"}).status_code == 422
    assert client.get("/api/analyses", headers=h, params={"page_size": 1000}).status_code == 422


def test_bookmark_toggle_and_filter(client, alice):
    ids = _seed(client, alice["headers"])
    h = alice["headers"]
    target = ids["consulting.docx"]
    res = client.patch(f"/api/analyses/{target}", headers=h, json={"bookmarked": True})
    assert res.status_code == 200 and res.json()["bookmarked"] is True
    marked = client.get("/api/analyses", headers=h, params={"bookmarked": True}).json()
    assert [i["id"] for i in marked["items"]] == [target]
    client.patch(f"/api/analyses/{target}", headers=h, json={"bookmarked": False})
    assert client.get("/api/analyses", headers=h, params={"bookmarked": True}).json()["total"] == 0
    assert client.patch(f"/api/analyses/{target}", headers=h, json={"bookmarked": "maybe"}).status_code == 422


def test_delete_single_and_all(client, alice):
    ids = _seed(client, alice["headers"])
    h = alice["headers"]
    target = ids["cv-aisha.txt"]
    assert client.delete(f"/api/analyses/{target}", headers=h).status_code == 200
    assert client.get(f"/api/analyses/{target}", headers=h).status_code == 404
    assert client.delete(f"/api/analyses/{target}", headers=h).status_code == 404
    assert client.get("/api/analyses", headers=h).json()["total"] == 3
    res = client.delete("/api/analyses", headers=h)
    assert res.status_code == 200 and "3" in res.json()["detail"]
    assert client.get("/api/analyses", headers=h).json()["total"] == 0


def test_user_records_are_isolated(client, alice, bob):
    ids = _seed(client, alice["headers"])
    target = ids["acme-invoice.pdf"]
    hb = bob["headers"]
    assert client.get("/api/analyses", headers=hb).json()["total"] == 0
    assert client.get(f"/api/analyses/{target}", headers=hb).status_code == 404
    assert client.patch(f"/api/analyses/{target}", headers=hb, json={"bookmarked": True}).status_code == 404
    assert client.delete(f"/api/analyses/{target}", headers=hb).status_code == 404
    assert client.delete("/api/analyses", headers=hb).status_code == 200  # deletes only Bob's (none)
    assert client.get("/api/analyses/stats", headers=hb).json()["total"] == 0
    # Alice's data is untouched.
    alice_item = client.get(f"/api/analyses/{target}", headers=alice["headers"]).json()
    assert alice_item["bookmarked"] is False
    assert client.get("/api/analyses", headers=alice["headers"]).json()["total"] == 4


def test_account_deletion_removes_analyses(client, alice, db_path):
    _seed(client, alice["headers"])
    from .conftest import PASSWORD
    assert client.request("DELETE", "/api/users/me", headers=alice["headers"],
                          json={"password": PASSWORD}).status_code == 200
    assert sqlite3.connect(db_path).execute("SELECT COUNT(*) FROM analyses").fetchone()[0] == 0


def test_stats(client, alice):
    _seed(client, alice["headers"])
    stats = client.get("/api/analyses/stats", headers=alice["headers"]).json()
    assert stats["total"] == 4
    assert sum(c["count"] for c in stats["by_category"]) == 4
    assert sum(stats["by_priority"].values()) == 4
    assert len(stats["per_day"]) == 14 and stats["per_day"][-1]["count"] == 4
    assert 0 < stats["average_confidence"] <= 1


def test_model_info(client, alice):
    info = client.get("/api/model", headers=alice["headers"]).json()
    assert info["dataset"]["type"] == "synthetic / illustrative"
    assert len(info["categories"]) == 8
    assert "heldout_synthetic" in info["evaluation"]
    assert info["uncertainty_policy"]["min_top_score"] == 0.5
    assert info["caveats"]


def test_security_headers(client):
    res = client.get("/api/health")
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
