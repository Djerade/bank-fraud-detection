# Entraînement + client MLflow (profil Compose `train`)
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml readme.md requirements.txt requirements-ml.txt /app/
COPY Config /app/Config
COPY fraud_detection /app/fraud_detection
COPY fraud_scoring /app/fraud_scoring

ENV PIP_DEFAULT_TIMEOUT=300
RUN pip install --no-cache-dir --retries=10 -r requirements-ml.txt

ENV PYTHONPATH=/app
ENV MLFLOW_TRACKING_URI=http://mlflow:5000
ENV MLFLOW_EXPERIMENT_NAME=bank-fraud-detection
ENV FRAUD_MODEL_PATH=/app/models/fraud_classifier.joblib

RUN chmod +x /app/fraud_detection/entrypoint-train-init.sh

# Entraînement manuel : docker compose run --rm ml-train
ENTRYPOINT ["python", "-m", "fraud_detection.train"]
CMD ["--register"]
