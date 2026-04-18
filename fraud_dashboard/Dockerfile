# Tableau de bord Streamlit (topic scoré) — contexte de build : racine du dépôt
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml readme.md requirements.txt /app/
COPY Config /app/Config
COPY fraud_dashboard /app/fraud_dashboard

RUN mkdir -p /app/.streamlit \
    && cp /app/fraud_dashboard/.streamlit/config.toml /app/.streamlit/config.toml

ENV PIP_DEFAULT_TIMEOUT=300
RUN pip install --no-cache-dir --retries=10 -e ".[dashboard]"

ENV PYTHONPATH=/app

EXPOSE 8501

CMD ["streamlit", "run", "fraud_dashboard/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--browser.gatherUsageStats=false"]
