# FraudShield Next.js Dashboard

Dashboard temps réel en Next.js pour la surveillance fraude. En **Docker Compose**, il remplace l’ancien tableau de bord Streamlit et lit le topic Kafka **`bank.transactions.scored`** (transactions enrichies par `fraud-scorer`).

## Lancer en local

```bash
cd fraud_dashboard/next-dashboard
npm install
npm run dev
```

Chaque `npm run build` exécute d’abord `npm run clean` (suppression de `.next`) pour éviter des artefacts ou diagnostics incohérents. Pour nettoyer seulement : `npm run clean`.

Ouvrir [http://localhost:3000](http://localhost:3000).

### Données : Kafka ou simulation

- **Sans** variable `KAFKA_BOOTSTRAP_SERVERS` : l’API `GET /api/dashboard` sert des données **simulées** (`meta.source === "simulated"`).
- **Avec** `KAFKA_BOOTSTRAP_SERVERS` : consommation **Kafka** (`kafkajs`), tampon en mémoire (`meta.source === "kafka"`).

Variables utiles (alignées sur `Config/` et le service Compose) :

| Variable | Rôle |
|----------|------|
| `KAFKA_BOOTSTRAP_SERVERS` | Brokers (ex. `localhost:9092` ou `kafka:29092`) |
| `KAFKA_TOPIC_SCORED` | Topic lu (défaut `bank.transactions.scored`) |
| `DASHBOARD_KAFKA_GROUP` | Group ID consumer (défaut `fraud-next-dashboard`) |
| `KAFKA_AUTO_OFFSET_RESET` | `earliest` ou `latest` (défaut `earliest`) |
| `DASHBOARD_USE_MOCK` | `1` ou `true` pour forcer la simulation même si Kafka est défini |

## Points clefs

- Design dashboard professionnel (cartes KPI + graphiques + tables).
- Route serveur `GET /api/dashboard` (agrégations dans `lib/snapshot.ts`).
- Mise à jour automatique toutes les 2 secondes côté client.
- Image Docker : `fraud_dashboard/next-dashboard/Dockerfile` (contexte de build = racine du dépôt).

## Évolutions possibles

- Auth et rôles.
- Export CSV / webhook d’alerting.
