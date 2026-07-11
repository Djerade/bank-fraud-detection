---
name: machine-constraints
description: La machine de dev (7,4 Go RAM) ne supporte pas la stack Docker complète
metadata:
  type: project
---

L'hôte de développement a **7,4 Go de RAM et 8 cœurs**, et ne peut pas faire tourner toute la stack Compose en même temps que l'environnement de travail habituel.

**Why:** Au repos, la VM Docker Desktop (`qemu-system-x86`) prend déjà ~1,5 Go, VS Code ~0,7 Go et Chrome ~1,3 Go. Le swap (8 Go) sature. Constaté : dashboard Next.js répondant en 224 s, redémarrages en boucle, daemon Docker renvoyant `DeadlineExceeded` / `grpc: the client connection is closing`, builds annulés, et conteneurs renommés `<hash>_<nom>` quand Docker n'arrive plus à les supprimer.

Deux règles pratiques :
- **Ne pas démarrer `spark-speed`** (JVM Spark, 1–2 Go) sauf besoin explicite de l'architecture Lambda. Il n'est pas nécessaire au flux `simulateur → Kafka → fraud-scorer → dashboard`.
- **L'entraînement ML est tué par l'OOM killer** (`exit 137`) si la stack tourne. `fraud_detection/ml.py` utilise `n_jobs=-1` (8 workers). Arrêter la stack (garder `mlflow`) et brider le parallélisme :
  `-e LOKY_MAX_CPU_COUNT=2 -e OMP_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 -e MKL_NUM_THREADS=1`

Éviter aussi `docker compose up -d --build` sur tous les services : les builds parallèles saturent le daemon. Builder service par service. Voir [[training-serving-skew]].

**How to apply:** Démarrer la stack sans Spark :
`docker compose up -d zookeeper kafka kafka-ui mlflow simulateur-api connecteur fraud-scorer fraud-dashboard`
Si Kafka bascule brièvement en `unhealthy`, Compose abandonne les services dépendants (`dependency failed to start`) — relancer alors `docker compose up -d simulateur-api connecteur`.
