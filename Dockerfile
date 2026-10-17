# DocPredict - single-container image: FastAPI serves the API and the built React app.

# ---- 1. Build the frontend -------------------------------------------------
FROM node:20-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- 2. Python runtime -----------------------------------------------------
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/app ./app
COPY backend/ml ./ml
# Retrain inside the image so the model always matches the installed scikit-learn version.
# Deterministic (seed 42): produces the same model and metrics as the committed artifacts.
RUN python -m ml.train

COPY --from=frontend /build/dist ./static

ENV DOCPREDICT_STATIC_DIR=/app/static \
    DOCPREDICT_DATA_DIR=/var/data \
    DOCPREDICT_ENABLE_DOCS=false
RUN mkdir -p /var/data

EXPOSE 8000
# Render (and most hosts) provide $PORT; default to 8000 elsewhere.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
