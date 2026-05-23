export interface Position {
  ticker: string;
  qty: number;
  avg_price: number;
  current_price: number;
  value: number;
  pnl_pct: number;
  weight: number;
  earnings_date: string | null;
}

export interface EarningsAlert {
  ticker: string;
  earnings_date: string;
  days_until: number;
}

export interface Portfolio {
  initial_cash: number;
  cash: number;
  currency: string;
  invested_amount: number;  // 실제 매수에 쓴 금액 (sum of qty * avg_price)
  total_value: number;      // 주식 현재 평가액만 (현금 제외)
  total_pnl_pct: number;    // (total_value - invested_amount) / invested_amount
  positions: Position[];
  last_updated: string;
}

export interface MomentumRanking {
  rank: number;
  ticker: string;
  momentum_pct: number;
  in_portfolio: boolean;
}

export interface RebalanceInfo {
  last_rebalance_date: string | null;
  next_rebalance_date: string;
  drift_alerts: string[];
  status: "healthy" | "drift_detected" | "rebalancing";
}

export interface NewsAlert {
  ticker: string;
  headline: string;
  sentiment: "danger" | "warning" | "neutral";
  timestamp: string;
}

export interface NewsItem {
  id: string;
  ticker: string | null;
  headline: string;
  summary_ko: string;
  summary_en: string | null;
  source: string;
  url: string;
  sentiment: "positive" | "negative" | "neutral";
  published_at: string;
  is_portfolio_related: boolean;
}

export interface BenchmarkReturn {
  label: string;
  ticker: string;
  return_pct: number;
}

export interface DashboardData {
  portfolio: Portfolio;
  momentum_ranking: MomentumRanking[];
  rebalance_info: RebalanceInfo;
  news_alerts: NewsAlert[];
  benchmarks: BenchmarkReturn[];
  earnings_alerts: EarningsAlert[];
}
