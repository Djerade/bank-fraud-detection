import { buildDashboardSnapshot, REFRESH_SECONDS } from "@/lib/snapshot";
import type { DashboardSnapshot, Transaction } from "@/lib/types";

const MAX_STORE = 6000;
const TX_PER_SECOND = 4;

const TX_TYPES = ["ATM", "POS", "Online"] as const;
const MERCHANTS = [
  "Retail",
  "Travel",
  "Groceries",
  "Healthcare",
  "Entertainment"
] as const;
const CARDS = ["Visa", "Mastercard", "Amex"] as const;
const LOCATIONS = [
  "Paris",
  "Lyon",
  "Marseille",
  "Toulouse",
  "Lille",
  "Nantes",
  "Nice",
  "Bordeaux",
  "Rennes",
  "Strasbourg"
];

type Store = {
  startedAt: number;
  lastTick: number;
  sequence: number;
  rows: Transaction[];
};

const globalStore = globalThis as typeof globalThis & { __fraudStore?: Store };

function rnd(min: number, max: number): number {
  return Math.random() * (max - min) + min;
}

function pick<T>(arr: readonly T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function generateTx(sequence: number): Transaction {
  const fraudScore = Number(rnd(0.01, 0.99).toFixed(4));
  const amount = Number(rnd(0.02, 1.8).toFixed(3));
  return {
    transaction_id: `tx-${Date.now()}-${sequence}`,
    customer_id: `cust-${Math.floor(rnd(1, 2000))}`,
    transaction_type: pick(TX_TYPES),
    merchant_category: pick(MERCHANTS),
    transaction_location: pick(LOCATIONS),
    card_type: pick(CARDS),
    transaction_amount_million: amount,
    fraud_score: fraudScore,
    fraud_predicted: fraudScore >= 0.5 ? 1 : 0,
    timestamp: new Date().toISOString()
  };
}

function ensureStore(): Store {
  if (!globalStore.__fraudStore) {
    const now = Date.now();
    const seed: Transaction[] = [];
    for (let i = 0; i < 600; i += 1) {
      seed.push(generateTx(i));
    }
    globalStore.__fraudStore = {
      startedAt: now,
      lastTick: now,
      sequence: seed.length,
      rows: seed
    };
  }
  return globalStore.__fraudStore;
}

function updateStream(store: Store): void {
  const now = Date.now();
  const elapsedSec = Math.max(1, Math.floor((now - store.lastTick) / 1000));
  const toCreate = elapsedSec * TX_PER_SECOND;
  for (let i = 0; i < toCreate; i += 1) {
    store.rows.push(generateTx(store.sequence + i));
  }
  store.sequence += toCreate;
  store.lastTick = now;
  if (store.rows.length > MAX_STORE) {
    store.rows = store.rows.slice(store.rows.length - MAX_STORE);
  }
}

export function getDashboardSnapshot(): DashboardSnapshot {
  const store = ensureStore();
  updateStream(store);
  return buildDashboardSnapshot(store.rows, {
    source: "simulated",
    refreshSeconds: REFRESH_SECONDS
  });
}
