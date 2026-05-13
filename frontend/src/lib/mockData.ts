import { DashboardData } from "./types";

// Current prices relative to avg_price (realistic small P&L swings for demo)
const CURRENT_PRICES: Record<string, number> = {
  AMD:  472.30,   // +2.9%
  MU:   812.45,   // +2.1%
  MRVL: 178.60,   // +4.5%
  QCOM: 231.80,   // -2.5%
  ARM:  224.30,   // +5.4%
  ON:   103.10,   // -3.9%
  TXN:  308.40,   // +3.5%
  AMAT: 458.70,   // +3.3%
  FTNT: 119.60,   // +3.5%
};

const AVG_PRICES: Record<string, number> = {
  AMD:  459.02,
  MU:   795.73,
  MRVL: 170.93,
  QCOM: 237.65,
  ARM:  212.76,
  ON:   107.29,
  TXN:  297.91,
  AMAT: 443.84,
  FTNT: 115.50,
};

const QTYS: Record<string, number> = {
  AMD:  0.218,
  MU:   0.1257,
  MRVL: 0.5853,
  QCOM: 0.421,
  ARM:  0.4703,
  ON:   0.9325,
  TXN:  0.3358,
  AMAT: 0.2254,
  FTNT: 0.8663,
};

function buildPositions() {
  const cash = 99.572;
  let stockValue = 0;
  const rawPositions = Object.keys(QTYS).map((ticker) => {
    const qty = QTYS[ticker];
    const avg = AVG_PRICES[ticker];
    const cur = CURRENT_PRICES[ticker];
    const value = qty * cur;
    stockValue += value;
    return { ticker, qty, avg_price: avg, current_price: cur, value };
  });
  const total = cash + stockValue;
  return rawPositions.map((p) => ({
    ...p,
    pnl_pct: ((p.current_price - p.avg_price) / p.avg_price) * 100,
    weight: (p.value / total) * 100,
  }));
}

export const MOCK_DATA: DashboardData = {
  portfolio: {
    initial_cash: 1000.0,
    cash: 99.572,
    currency: "USD",
    total_value: (() => {
      const positions = buildPositions();
      return 99.572 + positions.reduce((s, p) => s + p.value, 0);
    })(),
    total_pnl_pct: (() => {
      const positions = buildPositions();
      const total = 99.572 + positions.reduce((s, p) => s + p.value, 0);
      return ((total - 1000) / 1000) * 100;
    })(),
    positions: buildPositions(),
    last_updated: "2026-05-13 09:30 (뉴욕)",
  },

  momentum_ranking: [
    { rank: 1,  ticker: "NVDA",  momentum_pct: 38.4,  in_portfolio: false },
    { rank: 2,  ticker: "MSFT",  momentum_pct: 29.1,  in_portfolio: false },
    { rank: 3,  ticker: "AMAT",  momentum_pct: 22.7,  in_portfolio: true  },
    { rank: 4,  ticker: "MRVL",  momentum_pct: 19.3,  in_portfolio: true  },
    { rank: 5,  ticker: "FTNT",  momentum_pct: 17.8,  in_portfolio: true  },
    { rank: 6,  ticker: "AMD",   momentum_pct: 15.2,  in_portfolio: true  },
    { rank: 7,  ticker: "TXN",   momentum_pct: 13.9,  in_portfolio: true  },
    { rank: 8,  ticker: "ARM",   momentum_pct: 11.4,  in_portfolio: true  },
    { rank: 9,  ticker: "QCOM",  momentum_pct: 9.6,   in_portfolio: true  },
    { rank: 10, ticker: "MU",    momentum_pct: 7.3,   in_portfolio: true  },
    { rank: 11, ticker: "ON",    momentum_pct: 5.1,   in_portfolio: true  },
    { rank: 12, ticker: "CRWD",  momentum_pct: 3.8,   in_portfolio: false },
  ],

  rebalance_info: {
    last_rebalance_date: "2026-05-12",
    next_rebalance_date: "2026-06-01",
    drift_alerts: [],
    status: "healthy",
  },

  news_alerts: [],

  benchmarks: [
    { label: "Nasdaq 100", ticker: "QQQ", return_pct: 1.8 },
    { label: "S&P 500",    ticker: "SPY", return_pct: 0.9 },
    { label: "Dow Jones",  ticker: "DIA", return_pct: -0.3 },
  ],
};
