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
| GET | `/transaction_continuous` | Flux NDJSON (5–7 tx/s) ; avec `to_kafka=true`, chaque transaction est aussi publiée sur Kafka (`topic` optionnel) |
| POST | `/publish` | Génère et envoie vers Kafka (`count`, `fraud_rate`, `topic`, `interval_seconds`, …) |

Les variables `KAFKA_BOOTSTRAP_SERVERS` et `KAFKA_TOPIC_RAW` s’appliquent à `/publish` et à `/transaction_continuous?to_kafka=true`.

---

## Prérequis

- **Docker** et **Docker Compose**
- Projet installé en mode éditable : `pip install -r requirements.txt` ou `pip install -e .` (voir `readme.md`). L’exploration Jupyter est indépendante : `requirements-notebooks.txt`.

---

## Démarrer Kafka (local)

Le dépôt définit un **cluster Kafka avec ZooKeeper** (3 brokers), **Kafka UI** et l’**API simulateur** dans un seul **`docker-compose.yml`** à la racine (services `zookeeper`, `kafka-1`, `kafka-2`, `kafka-3`, `kafka-ui`, `simulateur-api`, volumes persistants).

À la racine du dépôt :

```bash
docker compose up -d
```

- **Bootstrap depuis l’hôte** : `localhost:9092,localhost:9093,localhost:9094` (tous sur `127.0.0.1`)
- **ZooKeeper (hôte)** : `127.0.0.1:2181`
- **Kafka UI** (image **provectuslabs/kafka-ui**) : [http://127.0.0.1:8080](http://127.0.0.1:8080) — topics, messages, brokers
- **Réseau Docker** : `kafka-1:29092`, `kafka-2:29092`, `kafka-3:29092` (même port **interne** sur chaque hôte broker)

Réplication par défaut : facteur **3**, `min.insync.replicas` **2** (topics créés automatiquement héritent de ces défauts).

Changement majeur de stack ou données corrompues : supprimez les volumes nommés si besoin :

```bash
docker compose down --remove-orphans -v
docker compose up -d
```

Arrêt :

```bash
docker compose down
```

### Kafka + API simulateur (Compose)

Le service **`simulateur-api`** (build `simulateur/Dockerfile`) utilise  
**`KAFKA_BOOTSTRAP_SERVERS=kafka-1:29092,kafka-2:29092,kafka-3:29092`** (réseau interne Compose, pas `localhost`).

```bash
docker compose up -d --build
```

- Kafka (hôte) : ports **9092**, **9093**, **9094**
- Kafka UI : `127.0.0.1:8080`
- API : `127.0.0.1:8000` (Swagger `/docs`)

Le premier build peut être long (toutes les dépendances du `pyproject.toml`, dont la stack ML).

Le même fichier compose **monte le code** (`simulateur/`, `src/bank_fraud_detection/`) et lance l’API avec **`uvicorn --reload`** : une sauvegarde dans l’éditeur redémarre le serveur. Sur Docker Desktop, décommenter `WATCHFILES_FORCE_POLLING` sous `simulateur-api` si le reload ne réagit pas.

---

## Variables d’environnement

| Variable | Défaut | Rôle |
|----------|--------|------|
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092,localhost:9093,localhost:9094` | Liste des brokers (hôte) |
| `KAFKA_TOPIC_RAW` | `bank.transactions.raw` | Topic d’ingestion CSV / simulateur |
| `KAFKA_TOPIC_PROCESSED` | `bank.transactions.processed` | Topic par défaut du consommateur d’exemple |
| `FRAUD_CSV_PATH` | `data/FraudShield_Banking_Data.csv` | Chemin du CSV source |

---

## Commandes (depuis la racine du dépôt)

Exporter les brokers si besoin :

```bash
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092,localhost:9093,localhost:9094
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

**Connecteur HTTP** (`kafka-cluster/connecteur_api.py`) — récupère le flux NDJSON de **`GET /transaction_continuous`** (API sur `http://127.0.0.1:8000` par défaut ou `SIMULATEUR_API_BASE`) :

```bash
python kafka-cluster/connecteur_api.py --max 10
python kafka-cluster/connecteur_api.py --out-jsonl recu.jsonl
# Demande à l’API de publier en parallèle sur Kafka : --api-to-kafka
python kafka-cluster/connecteur_api.py --api-to-kafka --max 5
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

**Kafka « ne fonctionne pas »** — démarrez la stack et laissez **~30 s** (ZooKeeper puis les 3 brokers).

```bash
cd /chemin/vers/bank-fraud-detection
docker compose up -d
docker compose ps    # zookeeper, kafka-1, kafka-2, kafka-3 (et simulateur-api) « Up »
```

Vérification rapide : `./scripts/streaming/check_kafka.sh`. Dans les logs de chaque broker : **Kafka Server started**.

Sans conteneur actif, les scripts Python afficheront `NoBrokersAvailable` ou des timeouts.

**`docker compose ps` affiche `kafka` / `zookeeper` au lieu de `kafka-1` … `kafka-3`** — tu n’utilises pas le même compose que la racine du dépôt (ancien fichier, autre répertoire, ou conteneurs orphelins). À la racine du projet : `docker compose down --remove-orphans` puis `docker compose up -d --build` ; la colonne **SERVICE** doit lister `zookeeper`, `kafka-1`, `kafka-2`, `kafka-3`, etc.

**ZooKeeper « unhealthy »** — regarder `docker compose logs zookeeper --tail 100` (erreurs disque, permissions, données corrompues). Après correction du healthcheck dans le compose, recréer : `docker compose up -d --force-recreate zookeeper`.

**Ports `9092` / `9093` / `9094`, `2181` ou `8080` déjà utilisés** — anciens conteneurs : `docker compose down --remove-orphans`, ou `docker ps` pour identifier le processus.

**Brokers qui redémarrent en boucle** — ZooKeeper doit être **Up** avant les brokers ; vérifiez `docker compose logs zookeeper --tail 80`. Ressources Docker insuffisantes (RAM) : réduire à un broker en dev ou augmenter les limites Docker Desktop.

**Exposer Kafka sur le réseau local** — adaptez les mappings `127.0.0.1:…` et les `KAFKA_ADVERTISED_LISTENERS` `PLAINTEXT_HOST://…` pour une IP/hostname joignables par les clients ; en production, sécurisez (TLS, auth).

**« Len error » / taille ~1195725856 sur le port 2181** — même mécanisme que sur Kafka : un client envoie un **protocole qui n’est pas le protocole binaire ZooKeeper** (très souvent **HTTP** : onglet `http://localhost:2181`, outil de test, scanner). Les 4 premiers octets sont interprétés comme une taille de paquet → valeur absurde, ZK ferme la session (`WARN`). L’adresse **`172.23.0.1`** est en général la **passerelle Docker** : la connexion vient de **l’hôte**. Ce n’est pas une corruption de données ; supprimez la source (navigateur, mauvais healthcheck, etc.).

**`Unable to read additional data from client` depuis `127.0.0.1`** — connexions **très courtes** (souvent le **healthcheck** `nc -z` ou un probe TCP) : le client ferme tout de suite, ZK logue en **INFO**. Bruit normal, pas une panne.

**`fsync-ing the write ahead log … took … ms`** — disque ou **Docker Desktop** lent ; ZK reste utilisable mais la latence peut augmenter. Allouer plus de ressources au VM Docker, éviter le disque saturé, ou accepter les WARN en dev.

**`Started AdminServer … port 8080` dans les logs ZooKeeper** — interface **admin interne** au **conteneur** ZK (pas le port **8080** de **Kafka UI** sur l’hôte, sauf si tu as publié ce port par erreur). Ne pas confondre avec l’UI Kafka.

**`InvalidReceiveException` sur les ports 9092–9094** — même idée : **HTTP** ou autre protocole sur un port **Kafka** (navigateur, healthcheck mal configuré). Kafka ferme la connexion (WARN) ; le cluster peut continuer à fonctionner.
