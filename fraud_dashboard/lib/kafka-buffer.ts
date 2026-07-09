import { Kafka, logLevel } from "kafkajs";

import { buildDashboardSnapshot, REFRESH_SECONDS } from "@/lib/snapshot";
import type {
  CardType,
  DashboardSnapshot,
  MerchantCategory,
  Transaction,
  TransactionType
} from "@/lib/types";

const MAX_STORE = 6000;

type GlobalKafka = typeof globalThis & {
  __fraudKafkaRows?: Transaction[];
  __fraudKafkaLoopStarted?: boolean;
};

function getBuffer(): Transaction[] {
  const g = globalThis as GlobalKafka;
  if (!g.__fraudKafkaRows) {
    g.__fraudKafkaRows = [];
  }
  return g.__fraudKafkaRows;
}

function appendRow(tx: Transaction): void {
  const buf = getBuffer();
  buf.push(tx);
  if (buf.length > MAX_STORE) {
    buf.splice(0, buf.length - MAX_STORE);
  }
}

const TX_TYPES = new Set<string>(["ATM", "POS", "Online"]);

const CARD_TYPES = new Set<string>(["Visa", "Mastercard", "Amex", "Credit", "Debit"]);

const MERCHANT_ALIASES: Record<string, MerchantCategory> = {
  Electronics: "Retail",
  Grocery: "Groceries"
};

function coerceMerchant(raw: string): MerchantCategory {
  const mapped = MERCHANT_ALIASES[raw];
  if (mapped) {
    return mapped;
  }
  const allowed: MerchantCategory[] = [
    "Retail",
    "Travel",
    "Groceries",
    "Healthcare",
    "Entertainment",
    "ATM",
    "Electronics",
    "Grocery",
    "Fuel"
  ];
  return (allowed.includes(raw as MerchantCategory) ? raw : "Retail") as MerchantCategory;
}

/** Messages JSON du simulateur / fraud-scorer (topic scoré). */
export function normalizeKafkaRecord(raw: Record<string, unknown>): Transaction | null {
  if (raw.transaction_id === undefined || raw.transaction_id === null) {
    return null;
  }

  const transaction_id = String(raw.transaction_id);
  const customer_id =
    raw.customer_id !== undefined && raw.customer_id !== null ? String(raw.customer_id) : "";

  const tt = String(raw.transaction_type ?? "Online");
  const transaction_type = (TX_TYPES.has(tt) ? tt : "Online") as TransactionType;

  const merchant_category = coerceMerchant(String(raw.merchant_category ?? "Retail"));
  const transaction_location = String(raw.transaction_location ?? "");
  const ctRaw = String(raw.card_type ?? "Credit");
  const card_type = (CARD_TYPES.has(ctRaw) ? ctRaw : "Credit") as CardType;

  const transaction_amount_million = Number(raw.transaction_amount_million);
  const amt = Number.isFinite(transaction_amount_million) ? transaction_amount_million : 0;

  let fraud_score = Number(raw.fraud_score);
  if (!Number.isFinite(fraud_score)) {
    fraud_score = 0;
  }

  const fraud_predicted = Number(raw.fraud_predicted) === 1 ? 1 : 0;

  let timestamp: string;
  const scoredAt = raw._scored_at;
  if (typeof scoredAt === "number" && Number.isFinite(scoredAt)) {
    timestamp = new Date(scoredAt * 1000).toISOString();
  } else {
    const d = raw.transaction_date;
    const t = raw.transaction_time;
    if (typeof d === "string" && typeof t === "string") {
      const padded = t.length === 5 ? `${t}:00` : t;
      const ms = Date.parse(`${d}T${padded}`);
      timestamp = Number.isNaN(ms) ? new Date().toISOString() : new Date(ms).toISOString();
    } else {
      timestamp = new Date().toISOString();
    }
  }

  return {
    transaction_id,
    customer_id,
    transaction_type,
    merchant_category,
    transaction_location,
    card_type,
    transaction_amount_million: amt,
    fraud_score,
    fraud_predicted,
    timestamp
  };
}

export function isKafkaConfigured(): boolean {
  const forceMock = process.env.DASHBOARD_USE_MOCK === "1" || process.env.DASHBOARD_USE_MOCK === "true";
  if (forceMock) {
    return false;
  }
  const b = process.env.KAFKA_BOOTSTRAP_SERVERS?.trim();
  return Boolean(b);
}

export function getKafkaDashboardSnapshot(): DashboardSnapshot {
  const rows = [...getBuffer()];
  return buildDashboardSnapshot(rows, { source: "kafka", refreshSeconds: REFRESH_SECONDS });
}

export function startKafkaConsumerBackground(): void {
  const g = globalThis as GlobalKafka;
  if (g.__fraudKafkaLoopStarted) {
    return;
  }
  g.__fraudKafkaLoopStarted = true;

  const bootstrap = process.env.KAFKA_BOOTSTRAP_SERVERS?.trim();
  const topic = process.env.KAFKA_TOPIC_SCORED?.trim() || "bank.transactions.scored";
  const groupId = process.env.DASHBOARD_KAFKA_GROUP?.trim() || "fraud-next-dashboard";
  const fromBeginning =
    (process.env.KAFKA_AUTO_OFFSET_RESET ?? "earliest").toLowerCase() !== "latest";

  if (!bootstrap) {
    return;
  }

  const brokers = bootstrap.split(",").map((h) => h.trim()).filter(Boolean);

  void (async () => {
    try {
      const kafka = new Kafka({
        clientId: "fraud-next-dashboard",
        brokers,
        logLevel: logLevel.NOTHING
      });
      const consumer = kafka.consumer({ groupId });
      await consumer.connect();
      await consumer.subscribe({ topic, fromBeginning });
      await consumer.run({
        eachMessage: async ({ message }) => {
          try {
            const raw = JSON.parse(message.value?.toString() ?? "{}");
            if (typeof raw !== "object" || raw === null) {
              return;
            }
            const tx = normalizeKafkaRecord(raw as Record<string, unknown>);
            if (tx) {
              appendRow(tx);
            }
          } catch {
            /* message ignoré */
          }
        }
      });
    } catch (err) {
      console.error("[fraud-next-dashboard] Kafka:", err);
    }
  })();
}
