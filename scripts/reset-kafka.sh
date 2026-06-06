#!/bin/sh
# Réinitialise le volume Kafka (métadonnées corrompues / ancien cluster multi-brokers).
# Usage : ./scripts/reset-kafka.sh && docker compose up -d
set -eu
cd "$(dirname "$0")/.."
echo "Arrêt des services qui utilisent Kafka..."
docker compose stop kafka connecteur fraud-scorer spark-speed fraud-dashboard kafka-ui 2>/dev/null || true
echo "Suppression du conteneur Kafka..."
docker compose rm -f kafka 2>/dev/null || true
VOL=$(docker volume ls -q | grep -E 'kafka-data$' | head -1)
if [ -n "$VOL" ]; then
  echo "Suppression du volume : $VOL"
  docker volume rm "$VOL"
else
  echo "Aucun volume kafka-data trouvé (déjà propre ?)."
fi
echo "Redémarrage ZooKeeper + Kafka..."
docker compose up -d zookeeper kafka
echo "Attendre que Kafka soit healthy (jusqu'à ~3 min)..."
for i in $(seq 1 24); do
  st=$(docker inspect bank-fraud-detection-kafka-1 --format '{{.State.Health.Status}}' 2>/dev/null || echo missing)
  if [ "$st" = healthy ]; then
    echo "Kafka est healthy."
    exit 0
  fi
  sleep 10
done
echo "Kafka pas encore healthy — vérifier : docker logs bank-fraud-detection-kafka-1"
exit 1
