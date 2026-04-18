# Service scoring fraude (Kafka → joblib → Kafka)
# Contexte de build : racine du dépôt
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml readme.md requirements.txt /app/
COPY Config /app/Config
COPY fraud_scoring /app/fraud_scoring

ENV PIP_DEFAULT_TIMEOUT=300
RUN pip install --no-cache-dir --retries=10 -r requirements.txt

ENV PYTHONPATH=/app

# Montage attendu : ./models:/app/models:ro
CMD ["python", "-m", "fraud_scoring.kafka_scorer"]
