# Spark — architecture Lambda (deux couches)

| Couche | Service Compose | Rôle |
|--------|-------------------|------|
| **Vitesse** | `spark-speed` | Structured Streaming : Kafka → Parquet **bronze** (`/data/lake/bronze/transactions`) + **checkpoint**. |
| **Batch** | `spark-batch` (profil `batch`) | Job ponctuel : lit le **bronze** si présent, sinon **repli Kafka** ; agrégats → **gold** (`/data/lake/gold/batch_summary`). |

Variables d’environnement (défauts adaptés au `docker-compose.yml`) : `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_TOPIC`, `SPARK_BRONZE_PATH`, `SPARK_GOLD_PATH`, `SPARK_CHECKPOINT_SPEED`.

## Démarrage

```bash
docker compose up -d --build
```

Le service **`spark-speed`** tourne en continu (après téléchargement du connecteur Kafka par Spark au premier lancement).

## Couche batch (planifiable / manuelle)

```bash
docker compose --profile batch run --rm spark-batch
```

Le job s’arrête après avoir écrit le résumé **gold** en Parquet. À planifier avec cron, Airflow, etc.

## Développement local (sans Docker Spark)

```bash
pip install "pyspark==3.5.3"
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
spark-submit --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3 \
  --master 'local[*]' spark_lambda/speed_layer.py
```

Adapter `SPARK_BRONZE_PATH` / `SPARK_CHECKPOINT_SPEED` vers des répertoires locaux accessibles en écriture.

## Schéma JSON

Le parsing batch utilise `spark_lambda/transaction_schema.py` (transactions simulateur). Les messages **produceur.py** (champs `seq`, `source`, …) sont ignorés par le filtre `transaction_id`.
