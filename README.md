# DocPredict

DocPredict is a local web application that analyses uploaded documents (PDF, DOCX, TXT). For each document it:

- extracts the real text,
- classifies the document type with a **locally trained scikit-learn model**,
- builds an **extractive** summary and keywords,
- pulls out dates, amounts, reference numbers, emails, phone numbers and labelled fields,
- shows the model score, all category scores and a documented **uncertainty** flag,
- explains the prediction with **evidence sentences and term contributions** from the document and the model,
- assigns a separate, rule-based **attention level** (not a model output),
- saves the analysis metadata in SQLite so it can be searched, filtered, bookmarked and deleted.

Nothing is sent to third-party services. Uploaded files and their full text are deleted right after processing.

> **Important.** The classifier is trained on a **synthetic, illustrative** dataset. Its accuracy on real documents has not been independently measured. Results are not legal, medical or financial advice. See [Machine-learning model](#machine-learning-model) and [Known limitations](#known-limitations).

---

## Contents

1. [Quick start (Windows)](#quick-start-windows)
2. [Manual commands](#manual-commands)
3. [Deploying to Render](#deploying-to-render)
4. [Using the app](#using-the-app)
5. [Project structure](#project-structure)
6. [Configuration](#configuration)
7. [Machine-learning model](#machine-learning-model)
8. [Privacy and data retention](#privacy-and-data-retention)
9. [Security measures](#security-measures)
10. [API reference](#api-reference)
11. [Testing](#testing)
12. [Known limitations](#known-limitations)
13. [Verification report](#verification-report)

---

## Quick start (Windows)

**Requirements:** Windows 10/11, Python 3.10+ (tested with **3.11.9**), Node.js 18+ (tested with **24.12.0**, npm 11.6.2).

Open PowerShell in the project folder (the folder containing this README) and run:

```powershell
# 1. One-time setup: venv, Python + npm dependencies, backend\.env with a random secret,
#    trains the model if missing, writes sample documents to .\samples
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1

# 2. Start backend and frontend (opens two PowerShell windows)
powershell -ExecutionPolicy Bypass -File scripts\start.ps1
```

Then open **http://localhost:5173**. The API runs on http://127.0.0.1:8000. Interactive API docs are at http://127.0.0.1:8000/docs.

To stop the app, close the two windows or press `Ctrl+C` in each.

`-ExecutionPolicy Bypass` applies only to that one command. It is needed because Windows blocks unsigned scripts by default.

> **Long paths.** Windows limits paths to 260 characters unless long-path support is enabled. If the project lives in a very deeply nested folder, creating the Python virtual environment can fail. Setup then stops with an explanatory message. Move the project to a shorter path (for example `C:\docpredict`) and re-run setup.

## Manual commands

These are the same steps the scripts run, if you prefer to run them yourself (PowerShell, from the project folder):

```powershell
# Backend: create the venv and install dependencies
cd backend
py -3.11 -m venv .venv                       # or: python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env                  # then set DOCPREDICT_SECRET_KEY in .env (see below)
.venv\Scripts\python -m ml.train             # train + evaluate the model (about 15 s)
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend (second terminal)
cd frontend
npm ci
npm run dev                                  # http://localhost:5173, proxies /api to port 8000
```

Generate a secret key for `backend\.env`:

```powershell
backend\.venv\Scripts\python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Other useful commands:

| Purpose | Command |
|---|---|
| Run all checks (backend tests, frontend tests, production build) | `powershell -ExecutionPolicy Bypass -File scripts\test.ps1` |
| Backend tests only | `cd backend; .venv\Scripts\python -m pytest` |
| Frontend tests only | `cd frontend; npm test` |
| Frontend production build | `cd frontend; npm run build` |
| Serve the production build (port 4173, also proxies `/api`) | `cd frontend; npm run preview` |
| Retrain the model | `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Retrain` or `cd backend; .venv\Scripts\python -m ml.train` |
| Regenerate sample files | `cd backend; .venv\Scripts\python -m tests.samples ..\samples` |
| Live end-to-end API check (servers must be running) | `cd backend; .venv\Scripts\python -m tests.e2e_http` |

The database (`backend\data\docpredict.db`) is created automatically on first start.

## Deploying to Render

In production, DocPredict runs as **one free Render web service** with its data in a **free Neon PostgreSQL database**:

- The `Dockerfile` builds the React app, installs the backend, retrains the model (deterministic, so the result is identical to the committed one), and starts FastAPI.
- FastAPI serves both `/api` and the website, so there is one web address and no cross-origin setup.
- `render.yaml` describes the service for Render.

**Why an external database.** On Render's free plan the local disk is wiped on every restart, and a free instance restarts whenever it wakes from sleep. All accounts and saved analyses therefore live in PostgreSQL. Only uploaded files touch the local disk, briefly, during processing.

**Limits of the free setup:**

- **Sleep.** The site sleeps after about 15 minutes without visitors. The next visit takes about a minute while it wakes up.
- **Neon free plan.** Storage is small but ample for analysis metadata. Neon may pause the database when idle and resumes it automatically on the next query; the app reconnects on its own.
- **One instance only.** The in-memory login throttle assumes a single instance. Do not scale to more than one.

### Step 1: create the database (Neon)

1. Sign up at https://neon.tech (a free account; signing in with GitHub works) and create a project, for example `docpredict`. Pick a region close to your Render region.
2. On the project dashboard, click **Connect**. Copy the **connection string**. It looks like `postgresql://user:password@ep-xxxx.region.aws.neon.tech/neondb?sslmode=require`.
3. Keep it private. It contains the database password.

### Step 2: create the web service (Render)

1. On https://dashboard.render.com choose **New → Blueprint** and enter the repository URL (`https://github.com/ashh2403/docpredict-app`), or connect GitHub and pick the repository.
2. Render reads `render.yaml` and asks for **`DOCPREDICT_DATABASE_URL`**. Paste the Neon connection string. The plan shown should be **Free**.
3. Click **Apply**. The first build takes several minutes (npm install, pip install, model training).
4. When it shows **Live**, open the `https://docpredict-xxxx.onrender.com` address. `/api/health` should return `"status": "ok"`.

The app creates its tables on first start. Render generates `DOCPREDICT_SECRET_KEY` itself (`generateValue`), so it is never stored in the repository.

### Settings

The container sets:
- `DOCPREDICT_STATIC_DIR`: the built website;
- `DOCPREDICT_ENABLE_DOCS=false`: no public API docs;
- `DOCPREDICT_DATA_DIR=/var/data`: temp files only.

`render.yaml` adds:
- `DOCPREDICT_ENABLE_HSTS=true`: Render serves HTTPS;
- the secret key;
- the database URL.

If `DOCPREDICT_DATABASE_URL` is missing in production mode, the app falls back to SQLite and **logs a warning**, because that data would be lost on the next restart.

To run the same single-server production mode locally (PowerShell, from the project folder):

```powershell
cd frontend; npm run build; cd ..\backend
$env:DOCPREDICT_STATIC_DIR = "..\frontend\dist"; $env:DOCPREDICT_ENABLE_DOCS = "false"
# optional: $env:DOCPREDICT_DATABASE_URL = "postgresql://user:password@host/db?sslmode=require"
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
# open http://127.0.0.1:8010
```

## Using the app

1. **Create an account** at `/register`. The password needs at least 8 characters, including a letter and a number.
2. **Analyze document**: drag a PDF, DOCX or TXT file (up to 10 MB) onto the upload area. Ready-made test files are in `samples\`:
   - `sample_invoice.pdf`, `sample_contract.docx`, `sample_resume.pdf`, `sample_medical_report.txt`, `sample_legal_notice.docx`: normal documents.
   - `sample_out_of_scope_recipe.txt`: a recipe. The model has no matching category, so the result is flagged **Uncertain**.
   - `invalid_scanned_image_only.pdf` and `invalid_not_really_a.pdf`: rejected by server-side validation.
3. The **result page** shows:
   - the predicted type and model score, with every category's score;
   - the reasons, if the result is uncertain;
   - the extractive summary;
   - evidence sentences with highlighted terms, plus the terms that supported the prediction and those that pointed to the runner-up;
   - keywords and extracted details;
   - the attention level and its reasons.
4. **History**: search (file names, summaries, keywords, type), filter by type, attention level, bookmarked or uncertain, sort, and paginate. Bookmark and delete from the list.
5. **Dashboard**: live totals, a 14-day activity chart, the document-type breakdown, recent analyses and attention levels.
6. **Model & accuracy**: the real evaluation metrics, calibration chart, confusion matrix, uncertainty policy and caveats.
7. **Settings**:
   - change your name, theme (light, dark or system; saved to your profile) and password;
   - delete all analyses, or delete your account;
   - sign out.

## Project structure

```
docpredict/
├── backend/
│   ├── app/
│   │   ├── main.py            FastAPI app, CORS, security headers (incl. CSP), startup (DB init, temp cleanup, model load)
│   │   ├── frontend.py        serves the built React app in single-service (production) mode
│   │   ├── config.py          settings from environment / backend\.env
│   │   ├── database.py        SQLAlchemy engine + session (SQLite)
│   │   ├── models.py          User, RevokedToken, Analysis tables
│   │   ├── schemas.py         request/response validation (Pydantic)
│   │   ├── security.py        bcrypt hashing, JWT, auth dependency, logout revocation, login throttling
│   │   ├── routers/           auth, users, analyses, model_info
│   │   └── services/
│   │       ├── extraction.py  file validation + PDF/DOCX/TXT text extraction
│   │       ├── classifier.py  model loading, prediction, evidence-based explanation
│   │       ├── uncertainty.py documented uncertainty policy
│   │       ├── insights.py    summary, keywords, field extraction, rule-based priority
│   │       ├── analyzer.py    upload → temp file → analysis → guaranteed cleanup
│   │       ├── text_utils.py  sentence splitting, tokenisation
│   │       └── categories.py  category list + shared text normalisation
│   ├── ml/
│   │   ├── dataset.py         reproducible synthetic corpus generator (seed 42)
│   │   ├── train.py           training, hyper-parameter search, evaluation, metrics.json
│   │   ├── data/              hand-written development and blind evaluation sets
│   │   └── artifacts/         model.joblib + metrics.json (generated by train.py)
│   ├── tests/                 pytest suite, sample-file builders, live e2e script
│   ├── requirements.txt       runtime dependencies (pinned)
│   ├── requirements-dev.txt   + pytest, httpx, fpdf2
│   └── .env.example           configuration template (copy to .env)
├── frontend/
│   ├── src/
│   │   ├── pages/             Landing, Login/Register, Dashboard, Analyze, Result, History, Settings, ModelInfo
│   │   ├── components/        app shell, route guards, shared UI
│   │   ├── context/           auth, theme, toasts
│   │   ├── lib/               API client, types, formatting, evidence highlighting
│   │   ├── styles/global.css  design system (tokens for light/dark themes)
│   │   └── test/              Vitest + Testing Library tests
│   ├── package.json / package-lock.json
│   └── vite.config.ts         dev/preview servers proxy /api to the backend
├── scripts/                   setup.ps1, start.ps1, start-backend.ps1, start-frontend.ps1, test.ps1
├── Dockerfile                 production image (builds frontend, serves everything from FastAPI)
├── render.yaml                Render Blueprint (free web service; data in external PostgreSQL)
└── samples/                   generated sample documents (scripts\setup.ps1)
```

**Stack:**
- Backend: FastAPI 0.115, SQLAlchemy 2.0 with SQLite locally or PostgreSQL in production (psycopg 3), scikit-learn 1.6, pypdf 5, python-docx 1.1, bcrypt, PyJWT.
- Frontend: React 18, TypeScript 5.7, Vite 6, React Router 6, Recharts 2, lucide-react icons, and locally bundled Inter and Plus Jakarta Sans fonts (no external font requests).

## Configuration

All settings are read from environment variables or `backend\.env`. The template is `backend\.env.example`.

| Variable | Default | Meaning |
|---|---|---|
| `DOCPREDICT_SECRET_KEY` | *(none)* | JWT signing key, at least 32 characters. If unset, a temporary key is generated at startup and a warning is logged; every restart then signs all users out. `setup.ps1` writes a random one. |
| `DOCPREDICT_DATA_DIR` | `backend/data` | Location of the SQLite DB and the temp folder |
| `DOCPREDICT_DATABASE_URL` | `sqlite:///<data dir>/docpredict.db` | Database URL. SQLite, or PostgreSQL: a plain `postgresql://…` URL as given by Neon or Render works |
| `DOCPREDICT_TEMP_DIR` | `<data dir>/tmp` | Where uploads live briefly during processing |
| `DOCPREDICT_MAX_UPLOAD_MB` | `10` | Maximum upload size |
| `DOCPREDICT_MAX_PDF_PAGES` | `200` | Maximum PDF pages |
| `DOCPREDICT_MAX_TEXT_CHARS` | `200000` | Longer extracted text is truncated (and the result says so) |
| `DOCPREDICT_TOKEN_EXPIRE_MINUTES` | `120` | Session length |
| `DOCPREDICT_CORS_ORIGINS` | `http://localhost:5173,...` | Allowed browser origins, only needed for direct cross-origin API calls |

`backend\.env` and `backend\data\` are in `.gitignore`. Never commit them.

## Machine-learning model

**Algorithm.** TF-IDF features (word unigrams and bigrams, English stop words removed, numbers replaced by a placeholder) feed a multinomial logistic-regression model. `C` is chosen by 5-fold cross-validated log-loss on the training split (selected: `C = 16`).

**Categories (8):** Invoice, Contract / Agreement, Resume / CV, Medical Report, Financial Report, Research Paper, Meeting Minutes, Legal Notice.

**Training data: synthetic and illustrative.**
- `ml/dataset.py` generates 1,600 documents (200 per category) from hand-written sentence templates. Slot values are randomised, and the generator adds shared boilerplate, sentences borrowed from other categories (50% of documents) and random word dropout, so documents are not exact template copies.
- These are **not** real documents.
- The generator is seeded (seed 42), so retraining reproduces the same model. This was verified by retraining in a clean install and getting identical metrics.

**Evaluation (actual numbers from `backend/ml/artifacts/metrics.json`):**

| Evaluation set | n | Accuracy | Macro F1 | ECE* | Passed confidence policy | Accuracy on those |
|---|---|---|---|---|---|---|
| Held-out synthetic (25% stratified split) | 400 | 99.75% | 99.75% | 0.043 | 100% | 99.75% |
| Hand-written **blind** set | 16 | 100% (16/16) | 100% | 0.273 | 75% | 100% |
| Hand-written development set | 24 | 100% (24/24) | 100% | 0.278 | 79% | 100% |

\*ECE = expected calibration error: the average gap between the model score and observed accuracy.

How to read these numbers:

- **The held-out synthetic split comes from the same generator as the training data**, so it greatly overstates real-world accuracy. Its one error was a resume predicted as meeting minutes.
- **The development set is not independent.** It was written as an evaluation set, but it was then used to diagnose the first model. That model was under-confident and mis-classified 6 of 24, and the generator's vocabulary was broadened as a result. Its 100% is therefore optimistic.
- **The blind set was written before the generator was revised and was never used for any fitting or tuning decision.** It is tiny (2 per category) and written by the same author as the generator, so 16/16 has a very wide margin of error. It is **not** evidence of production-grade accuracy.
- **Calibration.** The served scores are raw softmax outputs. On hand-written text they are *under-confident*: average score about 72–73%, observed accuracy 100%. Temperature scaling was tried and **rejected**: the development set is perfectly separated, so the fitted temperature collapsed toward 0 and would have pushed every score to about 100%, including on wrong or out-of-scope documents. On unfamiliar real documents the scores could be over-confident. They are therefore labelled **"model score"**, never "probability".
- Real-world accuracy is **unknown**. An independent, labelled set of real documents would be needed to measure it.

**Uncertainty policy** (`app/services/uncertainty.py`). A result is flagged **Uncertain** when any of these holds:

| Rule | Threshold |
|---|---|
| Top model score | < 0.50 |
| Gap between the top two categories | < 0.15 |
| Extracted words | < 25 |
| Share of the document's content words seen in training (out-of-scope signal) | < 30% |

The thresholds are fixed design choices, not values tuned to a metric. Uncertain results still show the best guess, clearly labelled as such, together with the reasons.

**Explanations.** For a linear model, each term's contribution to a category equals its TF-IDF weight times the model coefficient. The result page shows:
- the strongest supporting terms;
- terms that favoured the runner-up category;
- the sentences containing the strongest supporting terms, with those terms highlighted.

This is an exact decomposition of the linear model's score, not a post-hoc approximation.

**Summary, keywords and fields** are computed without the classifier:
- The summary is **extractive**: the document's own highest-scoring sentences, in their original order.
- Keywords are ranked by in-document frequency × inverse document frequency from the training corpus.
- Fields come from regular expressions.

**Attention level** (`low`, `medium` or `high`) is a **rule-based** heuristic. It looks for urgency wording (such as "overdue", "final notice", "legal proceedings"), short deadlines ("within 7 days") and, only when the prediction is not uncertain, the document type. It is independent of the model score and is not a measure of importance or risk.

## Privacy and data retention

**Never stored:**
- the original file: it is written to a randomly named temp file, read, and deleted in a `finally` block, so also when processing fails. Leftovers from a crashed process are removed at the next startup;
- the full extracted text.

**Stored per analysis (SQLite):**
- the sanitised file name, file type, size, page count, and word and character counts;
- the predicted type, all category scores, the uncertainty flag and its reasons, and the model version;
- the explanation: terms and up to 4 evidence sentences;
- the extractive summary and keywords;
- the extracted fields: dates, amounts, reference numbers, **emails, phone numbers**, and labelled values;
- the attention level and its reasons;
- the bookmark flag, processing time and timestamp.

Summaries, evidence sentences and fields are **short excerpts of the document**, so they can contain personal information that appears in it.

**Stored per user:** email, name, bcrypt password hash, theme preference and timestamps. The IDs of signed-out tokens are kept until those tokens expire.

**Deletion:**
- Delete one analysis from its result page or from History.
- Delete all analyses: *Settings → Data & privacy*.
- Delete your account, which removes all of its analyses: *Settings → Data & privacy*, confirmed with your password.

Deletion removes the rows from the database. SQLite may keep freed pages inside the database file until it is vacuumed.

**No external calls.** All processing is local. Fonts and icons are bundled. No analytics.

## Security measures

**Implemented:**
- **Passwords** are hashed with bcrypt (cost 12). The password policy is enforced on the server.
- **Login.** Failed sign-ins return the same message whether or not the account exists, and a dummy hash check equalises timing. Sign-in is throttled after 5 failures for an email address within 15 minutes; this is in memory, per process.
- **Sessions** use signed JWTs (HS256) with expiry and a unique ID. **Logout revokes the token on the server.** Deleting an account also revokes the current token.
- **Every analysis query is scoped to the signed-in user.** Other users' records return 404, indistinguishable from a missing record.
- **Uploads are untrusted:**
  - only `.pdf`, `.docx` and `.txt` are accepted, and the extension must match the file's magic bytes;
  - the size limit is enforced while streaming;
  - encrypted PDFs are rejected, along with PDFs over the page limit, PDFs without a text layer, and malformed PDFs;
  - DOCX zip archives are checked before parsing (required parts, entry count, total uncompressed size, compression ratio) to block zip bombs;
  - TXT files containing binary data are rejected;
  - the user's file name is never used on disk, and the display name is sanitised (no path components or special characters).
- **Requests:** request validation messages do not echo submitted values. Security headers are set (`nosniff`, `DENY` framing, `no-referrer`, `no-store`). CORS is restricted to the configured origins. Search input is parameterised and LIKE wildcards are escaped.
- **Secrets** stay out of source: `backend\.env` is git-ignored, and `setup.ps1` generates a random key.

**This is not a production-hardened deployment.** Notable gaps:
- no HTTPS when run locally (on Render, HTTPS is provided by the platform and the app sends HSTS);
- the token is kept in `sessionStorage`, readable by JavaScript if an XSS bug existed. React escapes rendered content and a strict Content-Security-Policy (`script-src 'self'`, no inline or eval'd scripts) is sent, which reduces but does not eliminate that risk;
- login throttling lives in memory and works for a single process only;
- no email verification or password reset;
- no audit logging, malware scanning or rate limiting on uploads;
- no encryption at rest for the SQLite file;
- dependencies have not been through a formal security audit.

## API reference

All endpoints are under `/api`. Authenticated endpoints need `Authorization: Bearer <token>`. OpenAPI docs: http://127.0.0.1:8000/docs.

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Status and model version |
| POST | `/auth/register` | `{email, full_name, password}` → token + user |
| POST | `/auth/login` | `{email, password}` → token + user |
| POST | `/auth/logout` | Revoke the current token |
| GET / PATCH | `/users/me` | Read profile / update `{full_name?, theme?}` |
| POST | `/users/me/password` | `{current_password, new_password}` |
| DELETE | `/users/me` | `{password}`: delete the account and all analyses |
| POST | `/analyses` | Multipart `file` → full analysis (201) |
| GET | `/analyses` | List: `q, category, priority, bookmarked, uncertain, sort (newest, oldest, confidence, name), page, page_size` |
| GET | `/analyses/stats` | Totals, by category, by priority, last 14 days |
| GET / PATCH / DELETE | `/analyses/{id}` | Read / `{bookmarked}` / delete |
| DELETE | `/analyses` | Delete all of the user's analyses |
| GET | `/model` | Model info, evaluation metrics, policy, caveats |

Error responses use `{"detail": "<message>"}` with the status codes 401, 404, 409, 413, 422, 429 and 503.

## Testing

**Backend (pytest, 79 tests).** Run `cd backend; .venv\Scripts\python -m pytest`. To run the same suite against PostgreSQL, set `DOCPREDICT_TEST_DATABASE_URL` to a **disposable** database URL first. Its tables are dropped and recreated for every test. The tests cover:
- **Authentication:** registration, validation, duplicate emails, bcrypt storage, login success and failure, no account enumeration, throttling, forged and expired tokens, logout revocation, profile and theme updates, password change, account deletion.
- **Document parsing:** real PDF (fpdf2), DOCX (python-docx, including tables) and TXT (UTF-8 BOM, cp1252) files. Rejection of fake extensions, binaries, empty files, encrypted PDFs, image-only PDFs, truncated PDFs, non-Word zips, DOCX zip bombs and the page limit. Text truncation, file-name sanitisation and sentence splitting.
- **Model:** correct predictions on sample documents, determinism, uncertain handling for out-of-scope, very short and mixed documents, evidence drawn from the document itself, extractive summaries, keywords and fields, priority independent of confidence, metrics file integrity.
- **Production serving:** website routes fall back to `index.html`, real files and HEAD requests are served, unknown `/api` paths and missing assets return 404, path traversal cannot escape the build folder, CSP/HSTS/cache headers.
- **API:** upload, analyse and retrieve for each format; validation errors; 413 for oversized files; authentication required; temp-file cleanup on success *and* failure; nothing saved after a failure; full text and file not persisted; history search, filters, sort and pagination (including wildcard escaping); bookmarks; deleting one and all; **user isolation**; account deletion cascading to analyses; stats; model info; security headers.

**Frontend (Vitest + Testing Library, 21 tests).** Run `cd frontend; npm test`. The tests cover:
- the API client: tokens, error messages, 401 handling, query strings, an unreachable server;
- client-side validation and evidence highlighting;
- the sign-in, registration and sign-out flows, and redirection of anonymous users;
- the result page's honest display of uncertainty and its highlighted evidence;
- bookmarking, not-found handling, and history search.

**Live end-to-end** (`backend\tests\e2e_http.py`) drives the 18-step workflow through running servers with the files in `samples\`.

## Known limitations

- **The model is illustrative.** It was trained on synthetic data, and its real-world accuracy is unknown and probably lower than reported. It knows only 8 categories, and anything else is at best flagged uncertain. It works on English text only.
- **Scores are not calibrated probabilities** (see above).
- **No OCR.** Scanned PDFs or images without a text layer are rejected. Legacy `.doc`, `.rtf`, `.odt` and spreadsheets are not supported.
- PDF text extraction quality depends on how the PDF was produced. Multi-column layouts can produce out-of-order text.
- Summaries are extractive, so they can be choppy for documents written as lists or tables.
- Field extraction uses patterns and can miss or mis-read values. Dates are not normalised.
- **Attention level** is a keyword heuristic, not an assessment of importance, urgency or risk.
- **Single-user-machine design:** SQLite, in-process login throttling, no background job queue, and synchronous processing during the upload request.
- Search is a simple case-insensitive substring match over file name, summary, keywords and category.
- The Recharts 2.x line used here is no longer actively developed upstream (npm prints a deprecation notice). It works, but a future upgrade to Recharts 3 is advisable.

## Verification report

Run on 17 Oct 2026, Windows 11 Home (10.0.26200), Python 3.11.9, Node 24.12.0, Microsoft Edge (via playwright-core) for the browser checks.

**Passed:**

| Check | Result |
|---|---|
| Backend test suite (`pytest`) | **79 passed, 0 failed** |
| Frontend test suite (`vitest`) | **21 passed, 0 failed** |
| TypeScript type-check + production build (`npm run build`) | **Passed**, no warnings (pages are code-split; main chunk 213 kB / 68 kB gzip) |
| `scripts\test.ps1` | **All checks passed** |
| `scripts\setup.ps1` on the existing checkout | **Passed** |
| Backend test suite against **PostgreSQL 16** (`DOCPREDICT_TEST_DATABASE_URL`) | **79 passed, 0 failed** |
| Production mode backed by PostgreSQL: live HTTP workflow, then an account created, the server restarted with a fresh local data folder, and the account signed in again | **33/33 passed; data survived the restart** |
| `scripts\setup.ps1` **from scratch** (no venv, no node_modules, no `.env`, no trained model), followed by `scripts\test.ps1` in that copy | **Passed**: venv created, `.env` generated, model retrained with **identical metrics**, 71 + 21 tests (the suite before the deployment work) and the build passed |
| `scripts\start-backend.ps1` + `scripts\start-frontend.ps1` | **Passed**: both servers start, and `/api` is proxied through port 5173 |
| `npm run preview` (production build) | **Passed**: SPA, deep links and `/api` proxy on port 4173 |
| Live HTTP workflow through the frontend proxy (`tests.e2e_http`), covering all 18 required steps with real PDF, DOCX and TXT samples, invalid files, the size limit and two-user isolation | **33/33 checks passed**; temp upload folder empty afterwards |
| Real-browser UI run in Edge (registration, uploads of every format, uncertain and invalid files, result evidence, bookmarking and unbookmarking, history search and filters, deletion with confirmation, dashboard charts, model page, profile update, dark theme persisted to the profile and restored on next sign-in, sign-out with token revocation, account deletion) | **35/35 checks passed**, no unexpected console errors |
| Responsive layout at desktop (1440 px), tablet (820 px) and phone (390 px) for dashboard, analyze, result, history, settings, model, landing and login | **No horizontal overflow**; screenshots reviewed manually |
| **Production single-service mode** (built frontend served by FastAPI, docs off, HSTS on, separate data folder), run locally without Docker | **Passed**: live HTTP workflow 33/33; browser run 35/35 under the Content-Security-Policy with no blocked resources (this run found and fixed fonts blocked by the first CSP draft); website routes, assets, HEAD requests and 404s checked |

**Failed.** None outstanding. Problems found during verification were fixed and re-verified:
- a Windows PowerShell 5.1 stderr handling bug in `setup.ps1`;
- an incomplete virtual environment not being detected on re-run;
- a 206 px page overflow at tablet width, caused by an absolutely positioned screen-reader label escaping the table's scroll container;
- tablet history columns being cut off;
- duplicate toasts, slow chart animations, a "0%" runner-up label, and a number-only explanation term.

**Not tested:**

| Check | Status |
|---|---|
| Python 3.10 / 3.12 and Node 18–22 | **Untested.** Only Python 3.11.9 and Node 24.12.0 were used. |
| Browsers other than Microsoft Edge (Chromium), such as Firefox and Safari, and real mobile devices | **Untested.** Mobile and tablet were checked with Edge viewport emulation only. |
| `scripts\start.ps1` opening two visible windows | **Not observed.** It launches the two individually verified scripts with `Start-Process`; window behaviour could not be observed in this non-interactive session. |
| Screen-reader and keyboard-only usage | Semantic roles and labels are used and exercised by the tests, but no assistive-technology testing was done. |
| Accuracy on real-world documents | **Not measured** (no labelled real dataset). |
| Large-scale, concurrent-user or load testing; formal security review | **Not performed.** |
| **Docker image build**, the **live Render deployment** and a real **Neon** database | **Untested here.** PostgreSQL was tested with a local PostgreSQL 16 server, not Neon itself. Docker is not installed on this machine, so the image has not been built locally; the commands it runs were verified individually in production mode above. The first Render build is the first real build of the image. |
| Setup in a folder whose path exceeds the Windows path limit | Fails with a clear message and leaves no broken venv (verified). Setup does not work around the limit itself. |
