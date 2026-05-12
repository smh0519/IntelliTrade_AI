import os
import json
from utils.logger import logger

DATA_FILE = "data/mock_account.json"

def _init_mock_account():
    """초기 가상 계좌가 없으면 10,000 달러 및 계층형 장부로 세팅합니다."""
    if not os.path.exists("data"):
        os.makedirs("data", exist_ok=True)
    
    # 기존 V1 장부가 존재한다면 V2(계층형)로 마이그레이션하거나, 새로 만듭니다.
    need_init = True
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                data = json.load(f)
                if "positions" in data and "initial_cash" in data:
                    need_init = False # 이미 V2
            except:
                pass

    if need_init:
        default_data = {
            "initial_cash": 10000.0,
            "cash": 10000.0,
            "currency": "USD",
            "positions": {
                "N10_MEW": {}
            }
        }
        with open(DATA_FILE, "w") as f:
            json.dump(default_data, f, indent=4)
        logger.info("📄 [PaperTrading] N10-MEW 가상 장부가 새로 생성되었습니다.")

def get_virtual_balance():
    _init_mock_account()
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def execute_virtual_buy(symbol: str, quantity: float, price: float, strategy_tag: str):
    """지정된 전략(tag)의 장부에 주식을 기록하고, 현금을 차감하며 평단가를 갱신합니다."""
    data = get_virtual_balance()
    executed_price = price * 1.0005 # 슬리피지/수수료 0.05%
    total_cost = executed_price * quantity
    
    if data["cash"] < total_cost:
        logger.error(f"[PaperTrading] ❌ 현금 부족! (필요: {total_cost}, 잔고: {data['cash']})")
        return None

    # 현금 차감
    data["cash"] -= total_cost
    
    # 전략 버킷 가져오기 (없으면 생성)
    if strategy_tag not in data["positions"]:
        data["positions"][strategy_tag] = {}
        
    strat_bucket = data["positions"][strategy_tag]
    
    # 해당 종목 물타기(평단가 가중평균) 계산
    if symbol in strat_bucket:
        old_qty = strat_bucket[symbol]["qty"]
        old_avg = strat_bucket[symbol]["avg_price"]
        
        new_qty = old_qty + quantity
        # (기존 총 가치 + 새로운 총 가치) / 총 수량
        new_avg = ((old_qty * old_avg) + total_cost) / new_qty
        
        strat_bucket[symbol]["qty"] = new_qty
        strat_bucket[symbol]["avg_price"] = new_avg
    else:
        # 최초 매수
        strat_bucket[symbol] = {
            "qty": quantity,
            "avg_price": executed_price
        }
    
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)
        
    logger.info(f"[PaperTrading] 📝 [{strategy_tag}] 장부 기록 완료: {symbol} {quantity}주 매수 (평단: {strat_bucket[symbol]['avg_price']:.2f})")
    return executed_price

def execute_virtual_sell(symbol: str, quantity: float, price: float, strategy_tag: str):
    """지정된 전략(tag)의 장부에서 주식을 차감하고 현금을 증가시킵니다."""
    data = get_virtual_balance()
    executed_price = price * 0.9995 # 슬리피지/수수료 0.05%
    total_revenue = executed_price * quantity
    
    if strategy_tag not in data["positions"] or symbol not in data["positions"][strategy_tag]:
         logger.error(f"[PaperTrading] ❌ [{strategy_tag}] 장부에 {symbol} 주식이 없습니다.")
         return None

    strat_bucket = data["positions"][strategy_tag]
    if strat_bucket[symbol]["qty"] < quantity:
        logger.error(f"[PaperTrading] ❌ [{strategy_tag}] 매도 수량({quantity}) 부족.")
        return None

    # 주식 차감 및 현금 증가
    strat_bucket[symbol]["qty"] -= quantity
    data["cash"] += total_revenue
    
    # 전량 매도시 종목 제거
    if strat_bucket[symbol]["qty"] <= 0:
        del strat_bucket[symbol]
        
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)
        
    logger.info(f"[PaperTrading] 📝 [{strategy_tag}] 장부 기록 완료: {symbol} {quantity}주 매도 (+{total_revenue:.2f}$)")
    return executed_price
