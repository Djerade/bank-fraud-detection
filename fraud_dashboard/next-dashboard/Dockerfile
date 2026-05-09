# Dashboard Next.js — topic Kafka scoré (`bank.transactions.scored` par défaut).
# Build depuis la racine du dépôt :
#   docker build -f fraud_dashboard/next-dashboard/Dockerfile .
#
# Variables : KAFKA_BOOTSTRAP_SERVERS, KAFKA_TOPIC_SCORED, DASHBOARD_KAFKA_GROUP,
# KAFKA_AUTO_OFFSET_RESET (earliest|latest), DASHBOARD_USE_MOCK=1 pour forcer les données simulées.

FROM node:22-bookworm-slim AS deps
WORKDIR /app

COPY fraud_dashboard/next-dashboard/package.json fraud_dashboard/next-dashboard/package-lock.json ./
RUN npm ci

COPY fraud_dashboard/next-dashboard/ ./

RUN npm run build

ENV NODE_ENV=production
EXPOSE 3000

CMD ["npm", "start"]
