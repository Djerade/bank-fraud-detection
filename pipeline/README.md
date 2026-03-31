# Pipeline Kafka — ingestion

Publication des transactions du jeu **FraudShield** (`data/FraudShield_Banking_Data.csv`) vers un topic Kafka en **JSON**, puis lecture de démonstration des messages.

| Fichier | Rôle |
|---------|------|
| `csv_to_kafka.py` | Producteur : lit le CSV par blocs et envoie vers le topic brut. |
| `kafka_consume_sample.py` | Consommateur minimal (affichage de *n* messages). |
| `config.py` | Brokers, noms de topics, mapping des colonnes CSV → clés JSON. |

Un **traitement aval** (prétraitement, scoring fraude, alertes) pourra consommer le même topic ou un topic dérivé via un service Python, Kafka Streams, Flink, etc.

---

## Prérequis

- **Docker** et **Docker Compose**
- Dépendances Python : `pip install -r requirements.txt` (notamment `kafka-python`, `pandas`)

---

## Démarrer le cluster Kafka

À la racine du dépôt :

```bash
docker compose up -d
```

- **ZooKeeper** : port `2181`
- **3 brokers** Kafka (Confluent Community `cp-kafka` 7.6.1) : **bootstrap** depuis la machine hôte  
  `localhost:9092,localhost:9093,localhost:9094`

Arrêt :

```bash
docker compose down
```

---

## Variables d’environnement

| Variable | Défaut | Rôle |
|----------|--------|------|
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092,localhost:9093,localhost:9094` | Liste des brokers |
| `KAFKA_TOPIC_RAW` | `bank.transactions.raw` | Topic d’ingestion CSV |
| `KAFKA_TOPIC_PROCESSED` | `bank.transactions.processed` | Topic par défaut du consommateur d’exemple |
| `FRAUD_CSV_PATH` | `data/FraudShield_Banking_Data.csv` | Chemin du CSV source |

---

## Commandes (depuis la racine du dépôt)

Exporter les brokers si besoin :

```bash
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092,localhost:9093,localhost:9094
```

**Publier** des lignes vers le topic brut :

```bash
python -m pipeline.csv_to_kafka --max-rows 2000 --sleep-ms 1
```

**Lire** quelques messages sur le topic brut (le sample pointe par défaut vers `KAFKA_TOPIC_PROCESSED` ; pour l’ingestion, préciser le topic brut) :

```bash
python -m pipeline.kafka_consume_sample --topic bank.transactions.raw --max 5
```

Raccourci shell (publie un extrait, paramètres dans le script) :

```bash
chmod +x scripts/streaming/ingest_csv.sh
./scripts/streaming/ingest_csv.sh
```

---

## Format des messages

Les messages sont des objets JSON dont les clés correspondent à `CSV_TO_JSON_FIELD` dans `config.py` (snake_case, sans espaces dans les noms de champs).
