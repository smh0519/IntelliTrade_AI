export interface Position {
  ticker: string;
  qty: number;
  avg_price: number;
  current_price: number;
  value: number;
  pnl_pct: number;
  weight: number;
}

export interface Portfolio {
  initial_cash: number;
  cash: number;
  currency: string;
  total_value: number;
  total_pnl_pct: number;
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
}
