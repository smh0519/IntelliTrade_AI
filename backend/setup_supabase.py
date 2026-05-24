#!/usr/bin/env python3
"""
Supabase 테이블 생성 및 연결 테스트 스크립트
실행: python setup_supabase.py
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    print("❌ .env 파일에 SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY를 설정해주세요.")
    sys.exit(1)

from supabase import create_client

client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
  id           BIGSERIAL PRIMARY KEY,
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  cash         DECIMAL(12,4) NOT NULL,
  total_value  DECIMAL(12,4) NOT NULL,
  initial_cash DECIMAL(12,4) NOT NULL,
  pnl_pct      DECIMAL(8,4)  NOT NULL,
  positions    JSONB         NOT NULL
);

CREATE TABLE IF NOT EXISTS momentum_rankings (
  id         BIGSERIAL PRIMARY KEY,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  rankings   JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS trade_log (
  id           BIGSERIAL PRIMARY KEY,
  created_at   TIMESTAMPTZ DEFAULT NOW(),
  action       TEXT          NOT NULL CHECK (action IN ('buy', 'sell')),
  ticker       TEXT          NOT NULL,
  qty          DECIMAL(12,6) NOT NULL,
  price        DECIMAL(12,4) NOT NULL,
  total_amount DECIMAL(12,4) NOT NULL,
  strategy_tag TEXT          DEFAULT 'N10_MEW'
);

CREATE TABLE IF NOT EXISTS rebalance_log (
  id             BIGSERIAL PRIMARY KEY,
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  reason         TEXT    NOT NULL,
  new_portfolio  TEXT[]  NOT NULL,
  sold_tickers   TEXT[]  DEFAULT '{}',
  bought_tickers TEXT[]  DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_created_at ON portfolio_snapshots (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_momentum_rankings_created_at   ON momentum_rankings (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trade_log_created_at           ON trade_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rebalance_log_created_at       ON rebalance_log (created_at DESC);
"""

print(f"🔗 Supabase 연결 중... {SUPABASE_URL}")

try:
    # DDL은 rpc를 통해 실행
    client.rpc("exec_sql", {"sql": SCHEMA_SQL}).execute()
    print("✅ 테이블 생성 완료")
except Exception:
    # exec_sql 함수가 없는 경우 — 각 테이블 존재 여부를 insert test로 확인
    pass

# 연결 및 테이블 존재 확인
tables = ["portfolio_snapshots", "momentum_rankings", "trade_log", "rebalance_log"]
print("\n📋 테이블 상태 확인:")

all_ok = True
for table in tables:
    try:
        result = client.table(table).select("id").limit(1).execute()
        print(f"  ✅ {table}")
    except Exception as e:
        print(f"  ❌ {table} — {e}")
        all_ok = False

if all_ok:
    print("\n🎉 Supabase 연결 및 테이블 확인 완료!")
    print("   python main.py 를 실행하면 데이터가 Supabase로 전송됩니다.")
else:
    print("\n⚠️  일부 테이블이 없습니다.")
    print("   Supabase 대시보드 > SQL Editor 에서 아래 파일을 실행해주세요:")
    print("   backend/supabase_schema.sql")
