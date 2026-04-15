# Spark 3.5 + Python — jobs Lambda (vitesse + batch). Contexte build : racine du dépôt.
FROM apache/spark:3.5.3-python3

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/spark/work-dir

COPY spark/download-kafka-jars.sh /tmp/download-kafka-jars.sh
RUN chmod +x /tmp/download-kafka-jars.sh && /tmp/download-kafka-jars.sh

COPY Config /opt/spark/work-dir/Config
COPY spark_lambda /opt/spark/work-dir/spark_lambda

ENV PYTHONPATH=/opt/spark/work-dir

# root : évite soucis de permissions sur volumes montés (dev local).
USER root
