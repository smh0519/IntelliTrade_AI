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

-- 5. 실적 캘린더 (보유 종목 다음 실적 발표일)
CREATE TABLE IF NOT EXISTS earnings_calendar (
  ticker        TEXT PRIMARY KEY,
  earnings_date DATE,
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE earnings_calendar DISABLE ROW LEVEL SECURITY;

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

-- ── user_id 컬럼 마이그레이션 ────────────────────────────────────────
-- 이미 테이블이 존재하는 경우 아래 ALTER 문을 Supabase SQL Editor에서 실행하세요.
ALTER TABLE portfolio_snapshots  ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE momentum_rankings    ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE trade_log            ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE rebalance_log        ADD COLUMN IF NOT EXISTS user_id UUID;

CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_user_id ON portfolio_snapshots (user_id);
CREATE INDEX IF NOT EXISTS idx_momentum_rankings_user_id   ON momentum_rankings (user_id);
CREATE INDEX IF NOT EXISTS idx_trade_log_user_id           ON trade_log (user_id);
CREATE INDEX IF NOT EXISTS idx_rebalance_log_user_id       ON rebalance_log (user_id);

-- 6. 증권계좌 API 자격증명 (프론트엔드 설정 화면에서 저장)
CREATE TABLE IF NOT EXISTS user_broker_credentials (
  user_id          UUID PRIMARY KEY,
  api_key          TEXT,
  secret_key       TEXT,
  account_id       TEXT,
  base_url         TEXT,
  is_simulation_mode BOOLEAN DEFAULT TRUE,
  updated_at       TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE user_broker_credentials DISABLE ROW LEVEL SECURITY;
