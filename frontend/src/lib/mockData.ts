import { DashboardData } from "./types";

// 실제 매수가 (2026-05-13 기준)
const AVG_PRICES: Record<string, number> = {
  AMD:  448.51,
  MRVL: 164.58,
  MU:   766.96,
  ARM:  208.02,
  QCOM: 210.42,
  ON:   104.16,
  CRWD: 546.45,
  TXN:  295.32,
  PANW: 215.71,
};

// 초기 로딩용 — 매수가와 동일하게 세팅 (슬리피지 반영, 수익률 ≈ 0)
const CURRENT_PRICES: Record<string, number> = {
  AMD:  448.29,
  MRVL: 164.50,
  MU:   766.58,
  ARM:  207.92,
  QCOM: 210.31,
  ON:   104.11,
  CRWD: 546.18,
  TXN:  295.17,
  PANW: 215.60,
};

const QTYS: Record<string, number> = {
  AMD:  0.2231,
  MRVL: 0.6079,
  MU:   0.1304,
  ARM:  0.481,
  QCOM: 0.4755,
  ON:   0.9605,
  CRWD: 0.1831,
  TXN:  0.3388,
  PANW: 0.4638,
};

const CASH = 99.56;

function buildPositions() {
  let stockValue = 0;
  const raw = Object.keys(QTYS).map((ticker) => {
    const qty = QTYS[ticker];
    const avg = AVG_PRICES[ticker];
    const cur = CURRENT_PRICES[ticker];
    const value = qty * cur;
    stockValue += value;
    return { ticker, qty, avg_price: avg, current_price: cur, value };
  });
  const total = CASH + stockValue;
  return raw.map((p) => ({
    ...p,
    pnl_pct: ((p.current_price - p.avg_price) / p.avg_price) * 100,
    weight:  (p.value / total) * 100,
  }));
}

const PORTFOLIO_TICKERS = new Set(Object.keys(QTYS));

export const MOCK_DATA: DashboardData = {
  portfolio: {
    initial_cash:  1000.0,
    cash:          CASH,
    currency:      "USD",
    total_value: (() => {
      const pos = buildPositions();
      return CASH + pos.reduce((s, p) => s + p.value, 0);
    })(),
    total_pnl_pct: (() => {
      const pos = buildPositions();
      const total = CASH + pos.reduce((s, p) => s + p.value, 0);
      return ((total - 1000) / 1000) * 100;
    })(),
    positions:    buildPositions(),
    last_updated: "2026-05-13 (뉴욕)",
  },

  momentum_ranking: [
    { rank: 1,  ticker: "AMD",  momentum_pct: 109.9, in_portfolio: true  },
    { rank: 2,  ticker: "MRVL", momentum_pct: 102.3, in_portfolio: true  },
    { rank: 3,  ticker: "MU",   momentum_pct:  86.9, in_portfolio: true  },
    { rank: 4,  ticker: "ARM",  momentum_pct:  66.0, in_portfolio: true  },
    { rank: 5,  ticker: "QCOM", momentum_pct:  50.1, in_portfolio: true  },
    { rank: 6,  ticker: "ON",   momentum_pct:  38.4, in_portfolio: true  },
    { rank: 7,  ticker: "CRWD", momentum_pct:  29.7, in_portfolio: true  },
    { rank: 8,  ticker: "TXN",  momentum_pct:  22.1, in_portfolio: true  },
    { rank: 9,  ticker: "PANW", momentum_pct:  18.6, in_portfolio: true  },
    { rank: 10, ticker: "AMZN", momentum_pct:  14.3, in_portfolio: false },
    { rank: 11, ticker: "FTNT", momentum_pct:  11.2, in_portfolio: false },
    { rank: 12, ticker: "AMAT", momentum_pct:   8.7, in_portfolio: false },
  ],

  rebalance_info: {
    last_rebalance_date: "2026-05-13",
    next_rebalance_date: "2026-06-01",
    drift_alerts: [],
    status:       "healthy",
  },

  news_alerts: [],

  benchmarks: [
    { label: "Nasdaq 100", ticker: "QQQ", return_pct:  1.8 },
    { label: "S&P 500",    ticker: "SPY", return_pct:  0.9 },
    { label: "Dow Jones",  ticker: "DIA", return_pct: -0.3 },
  ],
};

// 사용되지 않는 변수 방지
void PORTFOLIO_TICKERS;
