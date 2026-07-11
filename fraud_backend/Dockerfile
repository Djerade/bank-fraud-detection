# Backend de scoring : réutilise l'image simulateur (FastAPI + scikit-learn +
# pandas + kafka-python) et ajoute le client MLflow léger (mlflow-skinny) pour
# charger le modèle @champion depuis le Registry. Contexte de build : racine du dépôt.
FROM bank-fraud-detection-simulateur:latest

ENV PIP_DEFAULT_TIMEOUT=300
RUN pip install --no-cache-dir --retries=10 "mlflow-skinny==2.19.0"

COPY fraud_scoring /app/fraud_scoring
COPY fraud_backend /app/fraud_backend

ENV PYTHONPATH=/app \
    GIT_PYTHON_REFRESH=quiet

EXPOSE 8001
CMD ["uvicorn", "fraud_backend.app:app", "--host", "0.0.0.0", "--port", "8001"]
