# Streaming Kafka — ingestion

Simulation de transactions (jeu **FraudShield**, CSV de référence sous `docs/FraudShield_Banking_Data.csv`), publication **JSON** vers Kafka, et lecture via scripts du dossier `kafka-cluster/`.

| Élément | Rôle |
|--------|------|
| `Config/config.py` | Brokers (`KAFKA_BOOTSTRAP_SERVERS`), **topic unique** (`KAFKA_TOPIC` → `TOPIC`). |
| `simulateur/` | CLI `python -m simulateur.transaction_simulator` (envoi Kafka avec `--kafka`), **API FastAPI** (`app.py`) : génération JSON / NDJSON **sans** Kafka. |
| `kafka-cluster/produceur.py` | Producteur minimal de démo (JSON). |
| `kafka-cluster/consumer.py` | Consommateur minimal (affichage des messages). |
| `kafka-cluster/connecteur_api.py` | Lit le flux NDJSON de `GET /transaction_continuous` ; **`--to-kafka`** publie chaque ligne sur le topic (pont API → Kafka). |

Un seul topic Kafka est utilisé par défaut (`KAFKA_TOPIC`, défaut `bank.transactions.raw`). Les scripts ajoutent automatiquement la racine du dépôt au `PYTHONPATH` (`_repo_root.py`).

---

## API simulateur (FastAPI)

Dossier : `simulateur/` (`app.py`, `schemas.py`, `transaction_simulator.py`, `Dockerfile`). Pour le **CLI** avec `--kafka`, la config brokers/topic vient de **`Config.config`** (package `Config/` à la racine).

**Docker** (recommandé) : `docker compose up -d --build` — Swagger : [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Démarrage ponctuel sur l’hôte (venv + `pip install -r requirements.txt`) :

```bash
PYTHONPATH=. uvicorn simulateur.app:app --reload --host 127.0.0.1 --port 8000
# ou : PYTHONPATH=. python -m simulateur
```

| Méthode | Chemin | Rôle |
|---------|--------|------|
| GET | `/health` | Santé du service |
| GET | `/transaction` | Une transaction (query : `fraud_rate`, `seed`) |
| POST | `/transactions` | Corps JSON : `count`, `fraud_rate`, `seed` → liste de transactions |
| GET | `/transaction_continuous` | Flux NDJSON (5–7 tx/s), query `fraud_rate` uniquement |

Les variables `KAFKA_BOOTSTRAP_SERVERS` et `KAFKA_TOPIC` s’appliquent au CLI simulateur (`--kafka`), au connecteur `--to-kafka` et aux autres scripts sous `kafka-cluster/` (via `Config.config`).

---

## Prérequis

- **Docker** et **Docker Compose** (parcours principal)
- Facultatif : `pip install -r requirements.txt` sur l’hôte pour notebooks ou essais Uvicorn locaux (`readme.md`). Jupyter : `requirements-notebooks.txt`.

---

## Démarrer Kafka (local)

Le dépôt définit un **Kafka avec ZooKeeper** (1 broker), **Kafka UI** et l’**API simulateur** dans un seul **`docker-compose.yml`** à la racine (services `zookeeper`, `kafka`, `kafka-ui`, `simulateur-api`, volumes persistants).

À la racine du dépôt :

```bash
docker compose up -d
```

- **Bootstrap depuis l’hôte** : `localhost:9092` (`127.0.0.1`)
- **ZooKeeper (hôte)** : `127.0.0.1:2181`
- **Kafka UI** (image **provectuslabs/kafka-ui**) : [http://127.0.0.1:8080](http://127.0.0.1:8080) — topics, messages, brokers
- **Réseau Docker** : `kafka:29092` (listener **PLAINTEXT** interne)

Réplication par défaut : facteur **1**, `min.insync.replicas` **1** (topics créés automatiquement héritent de ces défauts).

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
**`KAFKA_BOOTSTRAP_SERVERS=kafka:29092`** (réseau interne Compose, pas `localhost`).

```bash
docker compose up -d --build
```

- Kafka (hôte) : port **9092**
- Kafka UI : `127.0.0.1:8080`
- API : `127.0.0.1:8000` (Swagger `/docs`)

Le premier build peut être long (dépendances du `pyproject.toml`).

Le compose **monte** `simulateur/`, `Config/` et `kafka-cluster/` dans `simulateur-api` avec **`uvicorn --reload`** (rechargement surtout utile pour `simulateur/` et `Config/`). Sur Docker Desktop, décommenter `WATCHFILES_FORCE_POLLING` sous `simulateur-api` si le reload ne réagit pas.

---

## Variables d’environnement

| Variable | Défaut | Rôle |
|----------|--------|------|
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Brokers (liste séparée par virgules) |
| `KAFKA_TOPIC` | `bank.transactions.raw` | **Unique** topic utilisé par simulateur, producteur et consommateur CLI |

---

## Commandes

### Depuis Docker (recommandé)

Même réseau que Kafka, brokers déjà à `kafka:29092` dans le service `simulateur-api` :

```bash
docker compose exec simulateur-api python -m simulateur.transaction_simulator --kafka --count 20
docker compose exec simulateur-api bash -lc "cd /app/kafka-cluster && python produceur.py --count 3"
docker compose exec simulateur-api bash -lc "cd /app/kafka-cluster && python consumer.py --max 5"
docker compose exec simulateur-api bash -lc "cd /app/kafka-cluster && python consumer.py --follow"
```

**Connecteur HTTP** — API joignable depuis l’hôte sur le port publié (`SIMULATEUR_API_BASE` par défaut `http://127.0.0.1:8000` si vous lancez le script sur l’hôte ; depuis le conteneur, utiliser l’URL qui atteint l’API, ex. `http://simulateur-api:8000` si vous ajoutez un service outil sur le même réseau) :

```bash
python kafka-cluster/connecteur_api.py --max 10
python kafka-cluster/connecteur_api.py --out-jsonl recu.jsonl
python kafka-cluster/connecteur_api.py --to-kafka --max 50
docker compose exec simulateur-api bash -lc "cd /app/kafka-cluster && python connecteur_api.py --to-kafka --max 30 --base-url http://127.0.0.1:8000"
```

Les scripts sous `kafka-cluster/` fonctionnent aussi **sans** `PYTHONPATH` grâce à `_repo_root.py`.

### Sur l’hôte (Kafka sur `localhost:9092`)

```bash
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export KAFKA_TOPIC=bank.transactions.raw   # optionnel, c’est le défaut
PYTHONPATH=. python -m simulateur.transaction_simulator --kafka --count 20
PYTHONPATH=. python kafka-cluster/produceur.py --count 3
PYTHONPATH=. python kafka-cluster/consumer.py --max 5
```

Le consumer accepte `--topic` pour surcharger le défaut (`KAFKA_TOPIC` / `TOPIC`), et `--only-new` pour ne lire que les messages produits après son démarrage.

---

## Format des messages

Objets **JSON** alignés sur les champs du jeu FraudShield (identifiants de transaction, montants, type, lieu, indicateur de fraude simulé, etc.), en **snake_case** — voir `simulateur/transaction_simulator.py` (`generate_transaction`).

---

## Dépannage

**Kafka « ne fonctionne pas »** — démarrez la stack et laissez **~30 s** (ZooKeeper puis le broker).

```bash
cd /chemin/vers/bank-fraud-detection
docker compose up -d
docker compose ps    # zookeeper, kafka (et simulateur-api) « Up »
```

Dans les logs du broker : **Kafka Server started**.

Sans conteneur actif, les scripts Python afficheront `NoBrokersAvailable` ou des timeouts.

**`docker compose ps` affiche `kafka` / `zookeeper` au lieu de `kafka`** — tu n’utilises pas le même compose que la racine du dépôt (ancien fichier, autre répertoire, ou conteneurs orphelins). À la racine du projet : `docker compose down --remove-orphans` puis `docker compose up -d --build` ; la colonne **SERVICE** doit lister `zookeeper`, `kafka`, etc.

**ZooKeeper « unhealthy »** — regarder `docker compose logs zookeeper --tail 100` (erreurs disque, permissions, données corrompues). Après correction du healthcheck dans le compose, recréer : `docker compose up -d --force-recreate zookeeper`.

**Ports `9092`, `2181` ou `8080` déjà utilisés** — anciens conteneurs : `docker compose down --remove-orphans`, ou `docker ps` pour identifier le processus.

**Broker qui redémarre en boucle** — ZooKeeper doit être **Up** avant le broker ; vérifiez `docker compose logs zookeeper --tail 80`. Ressources Docker insuffisantes (RAM) : augmenter les limites Docker Desktop.

**Exposer Kafka sur le réseau local** — adaptez les mappings `127.0.0.1:…` et les `KAFKA_ADVERTISED_LISTENERS` `PLAINTEXT_HOST://…` pour une IP/hostname joignables par les clients ; en production, sécurisez (TLS, auth).

**« Len error » / taille ~1195725856 sur le port 2181** — même mécanisme que sur Kafka : un client envoie un **protocole qui n’est pas le protocole binaire ZooKeeper** (très souvent **HTTP** : onglet `http://localhost:2181`, outil de test, scanner). Les 4 premiers octets sont interprétés comme une taille de paquet → valeur absurde, ZK ferme la session (`WARN`). L’adresse **`172.23.0.1`** est en général la **passerelle Docker** : la connexion vient de **l’hôte**. Ce n’est pas une corruption de données ; supprimez la source (navigateur, mauvais healthcheck, etc.).

**`Unable to read additional data from client` depuis `127.0.0.1`** — connexions **très courtes** (souvent le **healthcheck** `nc -z` ou un probe TCP) : le client ferme tout de suite, ZK logue en **INFO**. Bruit normal, pas une panne.

**`fsync-ing the write ahead log … took … ms`** — disque ou **Docker Desktop** lent ; ZK reste utilisable mais la latence peut augmenter. Allouer plus de ressources au VM Docker, éviter le disque saturé, ou accepter les WARN en dev.

**`Started AdminServer … port 8080` dans les logs ZooKeeper** — interface **admin interne** au **conteneur** ZK (pas le port **8080** de **Kafka UI** sur l’hôte, sauf si tu as publié ce port par erreur). Ne pas confondre avec l’UI Kafka.

**`InvalidReceiveException` sur le port 9092** — même idée : **HTTP** ou autre protocole sur un port **Kafka** (navigateur, healthcheck mal configuré). Kafka ferme la connexion (WARN) ; le broker peut continuer à fonctionner.

**`kafka-console-consumer` dans `docker compose exec kafka`** — utiliser le bootstrap **réseau Docker** (listener **PLAINTEXT**, port **29092**) plutôt que `localhost:9092` (listener **hôte** dans le conteneur) :

```bash
docker compose exec kafka kafka-console-consumer \
  --bootstrap-server kafka:29092 \
  --topic bank.transactions.raw \
  --from-beginning
```

Sur la **machine hôte**, utilisez `localhost:9092` (Python, outils locaux).
