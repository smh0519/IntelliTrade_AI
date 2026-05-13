-- IntelliTrade AI — Supabase 스키마
-- Supabase 대시보드 > SQL Editor 에서 전체 실행

-- 1. 포트폴리오 스냅샷 (매 1시간 기록)
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
  id           BIGSERIAL PRIMARY KEY,
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  cash         DECIMAL(12,4) NOT NULL,
  total_value  DECIMAL(12,4) NOT NULL,
  initial_cash DECIMAL(12,4) NOT NULL,
  pnl_pct      DECIMAL(8,4)  NOT NULL,
  positions    JSONB         NOT NULL  -- {"AMD": {"qty":0.218,"avg_price":459.02,"current_price":472.3}, ...}
);

-- 2. 모멘텀 랭킹 스냅샷 (매 1시간 기록)
CREATE TABLE IF NOT EXISTS momentum_rankings (
  id         BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  rankings   JSONB NOT NULL  -- [{"rank":1,"ticker":"NVDA","momentum_pct":38.4}, ...]
);

-- 3. 거래 내역 (매수/매도 발생 시 기록)
CREATE TABLE IF NOT EXISTS trade_log (
  id           BIGSERIAL PRIMARY KEY,
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  action       TEXT        NOT NULL CHECK (action IN ('buy', 'sell')),
  ticker       TEXT        NOT NULL,
  qty          DECIMAL(12,6) NOT NULL,
  price        DECIMAL(12,4) NOT NULL,
  total_amount DECIMAL(12,4) NOT NULL,
  strategy_tag TEXT        DEFAULT 'N10_MEW'
);

-- 4. 리밸런싱 이력 (리밸런싱 완료 시 기록)
CREATE TABLE IF NOT EXISTS rebalance_log (
  id            BIGSERIAL PRIMARY KEY,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  reason        TEXT    NOT NULL,
  new_portfolio TEXT[]  NOT NULL,  -- ['AMD','MU','MRVL', ...]
  sold_tickers  TEXT[]  DEFAULT '{}',
  bought_tickers TEXT[] DEFAULT '{}'
);

-- 인덱스 (최신 데이터 조회 최적화)
CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_created_at ON portfolio_snapshots (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_momentum_rankings_created_at   ON momentum_rankings (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trade_log_created_at           ON trade_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rebalance_log_created_at       ON rebalance_log (created_at DESC);

-- RLS 비활성화 (서버-사이드 service_role 키로만 접근)
ALTER TABLE portfolio_snapshots  DISABLE ROW LEVEL SECURITY;
ALTER TABLE momentum_rankings    DISABLE ROW LEVEL SECURITY;
ALTER TABLE trade_log            DISABLE ROW LEVEL SECURITY;
ALTER TABLE rebalance_log        DISABLE ROW LEVEL SECURITY;
