"""Live end-to-end check against RUNNING servers (not collected by pytest).

Usage (backend and frontend running):
    .venv\\Scripts\\python -m tests.e2e_http                       # via the frontend proxy (port 5173)
    .venv\\Scripts\\python -m tests.e2e_http http://127.0.0.1:8000  # directly against the API

Exercises the full workflow with the real files in ..\\samples and prints PASS/FAIL per step.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

import httpx

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5173").rstrip("/")
SAMPLES = Path(__file__).resolve().parents[2] / "samples"
results: list[tuple[str, bool, str]] = []


def check(step: str, ok: bool, detail: str = "") -> bool:
    results.append((step, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {step}{' - ' + detail if detail else ''}")
    return ok


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=60)
    email = f"e2e-{uuid.uuid4().hex[:8]}@example.com"
    pw = "E2eTest-Passw0rd"

    r = c.post("/api/auth/register", json={"email": email, "full_name": "E2E Tester", "password": pw})
    check("1. Register new account", r.status_code == 201, f"HTTP {r.status_code}")

    r = c.post("/api/auth/login", json={"email": email, "password": "wrong-pass1"})
    check("2a. Login rejects wrong password", r.status_code == 401, f"HTTP {r.status_code}")
    r = c.post("/api/auth/login", json={"email": email, "password": pw})
    ok = check("2b. Login with correct password", r.status_code == 200, f"HTTP {r.status_code}")
    if not ok:
        return 1
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}

    r = c.get("/api/analyses/stats", headers=h)
    check("3. Dashboard stats load (empty for new user)", r.status_code == 200 and r.json()["total"] == 0)

    expected = {
        "sample_invoice.pdf": "invoice", "sample_contract.docx": "contract", "sample_resume.pdf": "resume",
        "sample_medical_report.txt": "medical_report", "sample_legal_notice.docx": "legal_notice",
    }
    ids = {}
    for name, cat in expected.items():
        data = (SAMPLES / name).read_bytes()
        r = c.post("/api/analyses", headers=h, files={"file": (name, data)})
        body = r.json()
        ok = r.status_code == 201 and body.get("category") == cat
        check(f"4-12. Upload + analyse {name}", ok,
              f"HTTP {r.status_code}, predicted={body.get('category')}, score={body.get('confidence')}, "
              f"uncertain={body.get('is_uncertain')}, priority={body.get('priority')}")
        if r.status_code == 201:
            ids[name] = body["id"]
            check(f"   ...{name}: summary, keywords, evidence, fields present",
                  bool(body["summary"]) and bool(body["keywords"]) and bool(body["explanation"]["evidence"])
                  and isinstance(body["extracted_fields"], dict))

    r = c.post("/api/analyses", headers=h, files={"file": ("recipe.txt", (SAMPLES / "sample_out_of_scope_recipe.txt").read_bytes())})
    check("10. Out-of-scope document flagged uncertain", r.status_code == 201 and r.json()["is_uncertain"],
          "; ".join(r.json().get("uncertainty_reasons", [])))
    ids["recipe.txt"] = r.json().get("id")

    for bad in ("invalid_scanned_image_only.pdf", "invalid_not_really_a.pdf"):
        r = c.post("/api/analyses", headers=h, files={"file": (bad, (SAMPLES / bad).read_bytes())})
        check(f"5. Server rejects {bad}", r.status_code == 422, r.json().get("detail", ""))
    r = c.post("/api/analyses", headers=h, files={"file": ("big.txt", b"a " * (11 * 1024 * 1024 // 2))})
    check("5. Server rejects file over size limit", r.status_code == 413, f"HTTP {r.status_code}")

    inv = ids["sample_invoice.pdf"]
    r = c.get(f"/api/analyses/{inv}", headers=h)
    check("13. Open saved result", r.status_code == 200 and r.json()["id"] == inv)

    r = c.get("/api/analyses", headers=h, params={"q": "resume"})
    check("14a. Search history", r.status_code == 200 and any(i["filename"] == "sample_resume.pdf" for i in r.json()["items"]),
          f"{r.json().get('total')} match(es)")
    r = c.get("/api/analyses", headers=h, params={"category": "contract"})
    check("14b. Filter by category", r.json()["total"] == 1)
    r = c.get("/api/analyses", headers=h, params={"uncertain": "true"})
    check("14c. Filter uncertain", r.json()["total"] >= 1)

    r = c.patch(f"/api/analyses/{inv}", headers=h, json={"bookmarked": True})
    check("15a. Bookmark", r.status_code == 200 and r.json()["bookmarked"] is True)
    r = c.get("/api/analyses", headers=h, params={"bookmarked": "true"})
    check("15b. Bookmark filter", [i["id"] for i in r.json()["items"]] == [inv])
    r = c.patch(f"/api/analyses/{inv}", headers=h, json={"bookmarked": False})
    check("15c. Unbookmark", r.status_code == 200 and r.json()["bookmarked"] is False)

    r = c.patch("/api/users/me", headers=h, json={"full_name": "E2E Renamed", "theme": "dark"})
    check("16. Update profile and theme", r.status_code == 200 and r.json()["theme"] == "dark"
          and r.json()["full_name"] == "E2E Renamed")

    # Isolation: a second user cannot see or modify the first user's record.
    r2 = c.post("/api/auth/register", json={"email": f"other-{uuid.uuid4().hex[:8]}@example.com",
                                             "full_name": "Other", "password": pw})
    h2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}
    check("Isolation: other user gets 404 for foreign record", c.get(f"/api/analyses/{inv}", headers=h2).status_code == 404)
    check("Isolation: other user's history is empty", c.get("/api/analyses", headers=h2).json()["total"] == 0)
    c.request("DELETE", "/api/users/me", headers=h2, json={"password": pw})

    r = c.delete(f"/api/analyses/{inv}", headers=h)
    check("17a. Delete analysis", r.status_code == 200 and c.get(f"/api/analyses/{inv}", headers=h).status_code == 404)
    stats = c.get("/api/analyses/stats", headers=h).json()
    check("17b. Stats reflect deletion", stats["total"] == len(ids) - 1, f"total={stats['total']}")

    r = c.post("/api/auth/logout", headers=h)
    check("18a. Log out", r.status_code == 200)
    check("18b. Token rejected after logout", c.get("/api/users/me", headers=h).status_code == 401)

    # Clean up the test account (deletes its analyses too).
    h3 = {"Authorization": f"Bearer {c.post('/api/auth/login', json={'email': email, 'password': pw}).json()['access_token']}"}
    r = c.request("DELETE", "/api/users/me", headers=h3, json={"password": pw})
    check("Cleanup: delete test account", r.status_code == 200)

    failed = [s for s, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
