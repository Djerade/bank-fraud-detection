---
name: training-serving-skew
description: Piège majeur — train.py par défaut produit un modèle incompatible avec le scorer Kafka
metadata:
  type: project
---

`fraud_detection/train.py` doit être lancé avec `--data-path data/FraudShield_Banking_Data_clean.csv`, **jamais** avec ses options par défaut, sous peine de produire un modèle inutilisable par `fraud_scoring/kafka_scorer.py`.

**Why:** Les trois CSV de `data/` ne sont pas interchangeables :
- `FraudShield_Banking_Data.csv` (brut) : 50 000 lignes, **150 NaN** → `--raw-only` plante sur `train_test_split(stratify=...)` avec `ValueError: Input contains NaN`.
- `FraudShield_Banking_Data_features.csv` (**défaut de `load_training_frame`**) : contient déjà `hour_sin` et **24 colonnes one-hot** (`Transaction_Type_POS`, `Merchant_Category_ATM`, `Transaction_Location_*`…). Comme `hour_sin` est présent, `enrich_features()` est **sauté** → le modèle attend des dummies que `fraud_scoring/features.py` ne produit jamais → le scorer échoue sur *chaque* message avec `columns are missing: {...}`.
- `FraudShield_Banking_Data_clean.csv` : 49 996 lignes, 0 NaN, **25 colonnes brutes** → déclenche `enrich_features()`, la même fonction qu'au scoring. Colonnes alignées (36) des deux côtés. ✅

L'entraînement génère aussi `models/global_stats.json`, **indispensable** : sans lui, `enrich_features` calcule `amt.std()` sur une seule ligne au scoring → `NaN` → `predict()` échoue. Voir [[project-overview]].

Les artefacts de `notebooks/models/` ne sont **pas** des remplacements valides : `fraud_classifier.joblib` a été entraîné avec les dummies (incompatible), et `fraud_classifier_production.joblib` est un `dict {'pipeline', 'optimal_threshold'}`, pas un `Pipeline` — or `kafka_scorer.py` fait `joblib.load(...).predict(X)` sur un pipeline nu.

Attention aussi : `fraud_detection/entrypoint-train-init.sh` **saute** l'entraînement si le joblib existe *et* que MLflow a des runs. Pour forcer un ré-entraînement, contourner l'entrypoint :
`docker compose run --rm --no-deps --entrypoint python ml-train-init -m fraud_detection.train --register --data-path /app/data/FraudShield_Banking_Data_clean.csv`

**How to apply:** Après toute modification de `fraud_scoring/features.py`, ré-entraîner avec le CSV `clean`, sinon le scorer casse silencieusement (il logue l'erreur par message et le topic `bank.transactions.scored` reste vide → dashboard à zéro).
