# Image API simulateur (FastAPI) — contexte de build : racine du dépôt
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml readme.md requirements.txt /app/
COPY src /app/src
COPY simulateur /app/simulateur

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH=/app

EXPOSE 8000
CMD ["uvicorn", "simulateur.app:app", "--host", "0.0.0.0", "--port", "8000"]
