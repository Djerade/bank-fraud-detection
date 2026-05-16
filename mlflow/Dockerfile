FROM python:3.11-slim

RUN pip install --no-cache-dir "mlflow==2.19.0"
RUN mkdir -p /mlflow/db /mlflow/artifacts

HEALTHCHECK --interval=10s --timeout=5s --retries=12 --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health')"

EXPOSE 5000
VOLUME ["/mlflow"]

CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000", "--backend-store-uri", "sqlite:////mlflow/db/mlflow.db", "--default-artifact-root", "/mlflow/artifacts", "--serve-artifacts"]
