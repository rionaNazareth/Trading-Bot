import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

STATE_FILE = Path("state.json")


def _default_state() -> dict:
    return {
        "positions": [],
        "daily_pnl": 0.0,
        "trading_day": None,
        "trade_history": [],
        "last_run": None,
        "cumulative_pnl": 0.0,
        "peak_pnl": 0.0,
    }


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            logger.warning("Corrupt state.json, using default state")
    return _default_state()


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


def reset_daily_state(state: dict) -> dict:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if state.get("trading_day") != today:
        state["daily_pnl"] = 0.0
        state["trade_history"] = []
        state["trading_day"] = today
        logger.info(f"New trading day: {today}, daily state reset")
    return state


def get_position(state: dict, ticker: str) -> dict | None:
    for pos in state["positions"]:
        if pos["ticker"] == ticker:
            return pos
    return None


def add_position(
    state: dict,
    ticker: str,
    quantity: int,
    price: float,
    stop_loss: float,
    take_profit: float,
) -> dict:
    state["positions"].append(
        {
            "ticker": ticker,
            "quantity": quantity,
            "entry_price": price,
            "entry_time": datetime.now(timezone.utc).isoformat(),
            "stop_loss": stop_loss,
            "take_profit": take_profit,
        }
    )
    return state


def remove_position(state: dict, ticker: str) -> dict:
    state["positions"] = [p for p in state["positions"] if p["ticker"] != ticker]
    return state


def add_trade(
    state: dict,
    ticker: str,
    action: str,
    quantity: int,
    price: float,
    reasoning: str,
) -> dict:
    state["trade_history"].append(
        {
            "ticker": ticker,
            "action": action,
            "quantity": quantity,
            "price": price,
            "time": datetime.now(timezone.utc).isoformat(),
            "reasoning": reasoning,
        }
    )
    return state

