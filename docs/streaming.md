# Streaming Kafka — ingestion

Publication des transactions du jeu **FraudShield** (`data/FraudShield_Banking_Data.csv`) vers un topic Kafka en **JSON**, lecture d’exemple des messages, et **simulation** de transactions.

| Module | Rôle |
|--------|------|
| `bank_fraud_detection.streaming.csv_to_kafka` | Producteur : lit le CSV par blocs et envoie vers le topic brut. |
| `bank_fraud_detection.streaming.kafka_consume_sample` | Consommateur minimal (affichage de *n* messages). |
| `bank_fraud_detection.streaming.transaction_simulator` | Génère des transactions synthétiques (même schéma JSON). |
| `bank_fraud_detection.config` | Brokers, topics, chemin CSV, mapping colonnes → clés JSON. |

Un **traitement aval** (prétraitement, scoring fraude, alertes) pourra consommer le même topic ou un topic dérivé via un service Python, Kafka Streams, Flink, etc.

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

**Publier** des lignes vers le topic brut :

```bash
python -m bank_fraud_detection.streaming.csv_to_kafka --max-rows 2000 --sleep-ms 1
```

**Simuler** des transactions :

```bash
python -m bank_fraud_detection.streaming.transaction_simulator --count 50 --kafka --sleep-ms 1
```

**Lire** quelques messages sur le topic brut (le sample pointe par défaut vers `KAFKA_TOPIC_PROCESSED` ; pour l’ingestion, préciser le topic brut) :

```bash
python -m bank_fraud_detection.streaming.kafka_consume_sample --topic bank.transactions.raw --max 5
```

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
