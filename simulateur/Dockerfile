# Image API simulateur (FastAPI) — contexte de build : racine du dépôt
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml readme.md requirements.txt /app/
COPY Config /app/Config
COPY kafka-cluster /app/kafka-cluster
COPY simulateur /app/simulateur

# Réseau lent / PyPI instable : évite ReadTimeoutError sur files.pythonhosted.org
ENV PIP_DEFAULT_TIMEOUT=300
RUN pip install --no-cache-dir --retries=10 -r requirements.txt

ENV PYTHONPATH=/app

EXPOSE 8000
CMD ["uvicorn", "simulateur.app:app", "--host", "0.0.0.0", "--port", "8000"]
