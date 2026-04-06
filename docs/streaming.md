# Streaming Kafka — ingestion

Publication des transactions du jeu **FraudShield** (`data/FraudShield_Banking_Data.csv`) vers un topic Kafka en **JSON**, lecture d’exemple des messages, et **simulation** de transactions.

| Module | Rôle |
|--------|------|
| `bank_fraud_detection.streaming.csv_to_kafka` | Producteur : CSV **ou** JSONL (`--jsonl`, dont `-` = stdin / pipe simulateur). |
| `bank_fraud_detection.streaming.kafka_consume_sample` | Consommateur minimal (affichage de *n* messages). |
| `bank_fraud_detection.config` | Brokers, topics, chemin CSV, mapping colonnes → clés JSON. |
| `simulateur/` (racine du dépôt) | **CLI** `python -m simulateur.transaction_simulator`, **API FastAPI** (`app.py`), génération JSON et publication Kafka. |

Un **traitement aval** (prétraitement, scoring fraude, alertes) pourra consommer le même topic ou un topic dérivé via un service Python, Kafka Streams, Flink, etc.

---

## API simulateur (FastAPI)

Dossier : `simulateur/` à la racine du dépôt (`app.py`, `schemas.py`, `transaction_simulator.py`, `Dockerfile`). Le package `bank_fraud_detection` est importé depuis `src/` (installer le projet avec `pip install -e .`).

Démarrage **local** (après `pip install -r requirements.txt` ; sans installation : `PYTHONPATH=src:.`) :

```bash
uvicorn simulateur.app:app --reload --host 127.0.0.1 --port 8000
# ou, depuis la racine :
python -m simulateur
```

**Docker** (Kafka + API, détail plus bas) : `docker compose up -d --build` — documentation interactive : [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

| Méthode | Chemin | Rôle |
|---------|--------|------|
| GET | `/health` | Santé du service |
| GET | `/transaction` | Une transaction (query : `fraud_rate`, `seed`) |
| POST | `/transactions` | Corps JSON : `count`, `fraud_rate`, `seed` → liste de transactions |
| POST | `/publish` | Génère et envoie vers Kafka (`count`, `fraud_rate`, `topic`, `interval_seconds`, …) |

Les variables `KAFKA_BOOTSTRAP_SERVERS` et `KAFKA_TOPIC_RAW` s’appliquent à `/publish`.

---

## Prérequis

- **Docker** et **Docker Compose**
- Projet installé en mode éditable : `pip install -r requirements.txt` ou `pip install -e .` (voir `readme.md`). L’exploration Jupyter est indépendante : `requirements-notebooks.txt`.

---

## Démarrer Kafka (local)

Le `docker-compose.yml` lance **un seul broker Kafka en mode KRaft** (sans ZooKeeper), image **Confluent `cp-kafka` 7.6.1**. C’est plus stable sur Docker Desktop que l’ancien stack ZK + 3 brokers (timeouts, `fsync`).

À la racine du dépôt :

```bash
docker compose up -d
```

- **Bootstrap** : `localhost:9092` (port publié sur `127.0.0.1` uniquement)

**Première fois après un ancien compose** (ZooKeeper + `kafka-1` / `kafka-2` / `kafka-3`) : supprimez les conteneurs orphelins et les volumes si besoin :

```bash
docker compose down --remove-orphans -v
docker compose up -d
```

Arrêt :

```bash
docker compose down
```

### Kafka + API simulateur (Compose)

Le `docker-compose.yml` définit aussi le service **`simulateur-api`** (build `simulateur/Dockerfile`). L’API rejoint le broker avec **`KAFKA_BOOTSTRAP_SERVERS=kafka:29092`** (réseau interne Docker, pas `localhost`).

```bash
docker compose up -d --build
```

- Kafka (hôte) : `localhost:9092`
- API : `127.0.0.1:8000` (Swagger `/docs`)

Le premier build peut être long (toutes les dépendances du `pyproject.toml`, dont la stack ML).

Le même fichier compose **monte le code** (`simulateur/`, `src/bank_fraud_detection/`) et lance l’API avec **`uvicorn --reload`** : une sauvegarde dans l’éditeur redémarre le serveur. Sur Docker Desktop, décommenter `WATCHFILES_FORCE_POLLING` sous `simulateur-api` si le reload ne réagit pas.

---

## Variables d’environnement

| Variable | Défaut | Rôle |
|----------|--------|------|
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Brokers (un seul en dev) |
| `KAFKA_TOPIC_RAW` | `bank.transactions.raw` | Topic d’ingestion CSV / simulateur |
| `KAFKA_TOPIC_PROCESSED` | `bank.transactions.processed` | Topic par défaut du consommateur d’exemple |
| `FRAUD_CSV_PATH` | `data/FraudShield_Banking_Data.csv` | Chemin du CSV source |

---

## Commandes (depuis la racine du dépôt)

Exporter les brokers si besoin :

```bash
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

**Publier** des lignes CSV vers le topic brut :

```bash
python -m bank_fraud_detection.streaming.csv_to_kafka --max-rows 2000 --sleep-ms 1
```

**Chaîne simulateur → Kafka** (sans `--kafka` sur le simulateur : il n’envoie que sur stdout, `csv_to_kafka` publie) :

```bash
python -m simulateur.transaction_simulator --count 10 | \
  python -m bank_fraud_detection.streaming.csv_to_kafka --jsonl -
```

Ou depuis un fichier JSONL (`--out-file` du simulateur) :

```bash
python -m bank_fraud_detection.streaming.csv_to_kafka --jsonl ./transactions.jsonl
```

**Simuler** des transactions (CLI, après `pip install -e .` ; sinon `PYTHONPATH=src:.`) :

```bash
python -m simulateur.transaction_simulator --kafka --forever
# ou N messages, 1 toutes les 5 s par défaut vers Kafka :
python -m simulateur.transaction_simulator --kafka --count 20
# rafale (sans pause) : --interval-seconds 0
```

**Lire** quelques messages sur le topic brut (défaut du script : `bank.transactions.raw`) :

```bash
python -m bank_fraud_detection.streaming.kafka_consume_sample --max 5
```

**Suivre en temps réel** (chaque nouveau message s’affiche dès publication ; lancer **avant** ou **pendant** le simulateur / `csv_to_kafka`) :

```bash
python -m bank_fraud_detection.streaming.kafka_consume_sample --follow
```

Pour voir d’abord tout l’historique du topic puis les nouveaux messages :

```bash
python -m bank_fraud_detection.streaming.kafka_consume_sample --follow --from-beginning
```

Autre topic (ex. traité) : `--topic bank.transactions.processed`.

Raccourci shell :

```bash
chmod +x scripts/streaming/ingest_csv.sh
./scripts/streaming/ingest_csv.sh
```

---

## Format des messages

Les messages sont des objets JSON dont les clés correspondent à `CSV_TO_JSON_FIELD` dans `bank_fraud_detection.config` (snake_case).

---

## Dépannage

**Kafka « ne fonctionne pas »** — le broker est dans Docker : il faut **le démarrer** et laisser ~10 s le temps du démarrage.

```bash
cd /chemin/vers/bank-fraud-detection
docker compose up -d
docker compose ps    # le service kafka doit être « Up »
```

Vérification rapide : `./scripts/streaming/check_kafka.sh` (depuis la racine du dépôt, après `chmod +x` si besoin). Dans les logs : une ligne **Kafka Server started**.

Sans conteneur actif, les scripts Python afficheront `NoBrokersAvailable` ou des timeouts.

**Port `9092` déjà utilisé** — un ancien conteneur Kafka tourne encore : `docker compose down --remove-orphans` à la racine du dépôt, ou `docker ps` pour identifier le processus.

**« Aucun conteneur ne fonctionne » alors que les logs ZooKeeper s’affichaient** — avec l’ancien compose, ZooKeeper pouvait démarrer mais les brokers **échouaient** (ZK lent, timeouts). Le stack actuel **n’utilise plus ZooKeeper** ; vérifiez plutôt : `docker compose ps` (statut `Up`) et `docker compose logs kafka --tail 50` (ligne *Kafka Server started*).

**Exposer Kafka sur le réseau local** — remplacez `127.0.0.1:9092:9092` par `9092:9092` et adaptez `KAFKA_ADVERTISED_LISTENERS` (hostname/IP accessibles par les clients) ; en production, sécurisez (TLS, auth).

**Logs `zookeeper.ssl.truststore.* = null`** — Kafka affiche encore des clés liées à l’ancien mode « ZooKeeper » dans le dump de configuration. En **KRaft**, elles restent à `null` : **pas d’inquiétude**, ce n’est pas une erreur et ZooKeeper ne tourne pas.

**`InvalidReceiveException` / taille ~1195725856 sur le port 9092** — même idée que les « Len error » sur l’ancien port 2181 : un programme ouvre une connexion vers **`localhost:9092`** avec un **protocole qui n’est pas Kafka** (souvent **HTTP** : onglet navigateur `http://127.0.0.1:9092`, outil de test, healthcheck mal configuré). Kafka lit les premiers octets comme une taille de trame → valeur absurde, il **ferme la connexion** (WARN). Le broker continue de fonctionner. Cherchez ce qui interroge le port 9092 en HTTP sur votre machine.
