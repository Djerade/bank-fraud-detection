export type TransactionType = "ATM" | "POS" | "Online";
export type MerchantCategory =
  | "Retail"
  | "Travel"
  | "Groceries"
  | "Healthcare"
  | "Entertainment"
  | "ATM"
  | "Electronics"
  | "Grocery"
  | "Fuel";
export type CardType = "Visa" | "Mastercard" | "Amex" | "Credit" | "Debit";

export type Transaction = {
  transaction_id: string;
  customer_id: string;
  transaction_type: TransactionType;
  merchant_category: MerchantCategory;
  transaction_location: string;
  card_type: CardType;
  transaction_amount_million: number;
  fraud_score: number;
  fraud_predicted: 0 | 1;
  timestamp: string;
};

export type DashboardSnapshot = {
  meta: {
    source: "simulated" | "kafka";
    updatedAt: string;
    refreshSeconds: number;
  };
  metrics: {
    total: number;
    alerts: number;
    alertRatePct: number;
    criticalAlerts: number;
    avgAmountM: number;
    uniqueClients: number;
  };
  series: Array<{
    minute: string;
    volume: number;
    alerts: number;
    alertRatePct: number;
  }>;
  byType: Array<{
    name: string;
    volume: number;
    alerts: number;
  }>;
  byMerchant: Array<{
    name: string;
    volume: number;
    alerts: number;
    ratePct: number;
  }>;
  byLocation: Array<{
    name: string;
    alerts: number;
    ratePct: number;
  }>;
  scoreDistribution: Array<{
    bucket: string;
    count: number;
  }>;
  criticalTransactions: Transaction[];
  recentTransactions: Transaction[];
};
