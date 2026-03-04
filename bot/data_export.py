import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path("data")
TRADES_FILE = DATA_DIR / "trades.json"
DAILY_SUMMARIES_FILE = DATA_DIR / "daily_summaries.json"
LATEST_DECISIONS_FILE = DATA_DIR / "latest_decisions.json"


def _load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            logger.warning(f"Corrupt {path}, using default")
    return default


def _save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def append_trade(
    ticker: str,
    yf_symbol: str,
    action: str,
    quantity: int,
    price: float,
    reasoning: str,
    confidence: float | None,
    indicators: dict | None,
    stop_loss: float | None,
    take_profit: float | None,
    pnl: float | None,
) -> None:
    trades = _load_json(TRADES_FILE, [])
    now = datetime.now(timezone.utc).isoformat()
    trade_id = f"{now}_{ticker}_{action}"

    indicator_snapshot = None
    if indicators:
        indicator_snapshot = {
            "rsi_14": indicators.get("rsi_14"),
            "macd": indicators.get("macd"),
            "macd_signal": indicators.get("macd_signal"),
            "macd_histogram": indicators.get("macd_histogram"),
            "bb_pct": indicators.get("bb_pct"),
            "ema_trend": indicators.get("ema_trend"),
        }

    trades.append(
        {
            "id": trade_id,
            "ticker": ticker,
            "yf_symbol": yf_symbol,
            "action": action,
            "quantity": quantity,
            "price": price,
            "value": round(price * quantity, 2),
            "time": now,
            "reasoning": reasoning,
            "confidence": confidence,
            "indicators": indicator_snapshot,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "pnl": pnl,
        }
    )

    _save_json(TRADES_FILE, trades)


def update_daily_summary(state: dict) -> None:
    summaries = _load_json(DAILY_SUMMARIES_FILE, [])
    today = state.get("trading_day")
    if not today:
        return

    trades_today = state.get("trade_history", [])
    sells = [t for t in trades_today if t["action"] == "SELL"]
    buys = [t for t in trades_today if t["action"] == "BUY"]

    # Load all trades to compute wins/losses for today
    all_trades = _load_json(TRADES_FILE, [])
    today_pnls = [
        t["pnl"]
        for t in all_trades
        if t.get("time", "").startswith(today) and t.get("pnl") is not None
    ]

    wins = sum(1 for p in today_pnls if p > 0)
    losses = sum(1 for p in today_pnls if p <= 0)
    total_closed = wins + losses
    win_rate = round(wins / total_closed, 2) if total_closed > 0 else 0.0

    prev_cumulative = summaries[-1]["cumulative_pnl"] if summaries else 0.0

    entry = {
        "date": today,
        "pnl": round(state["daily_pnl"], 2),
        "cumulative_pnl": round(prev_cumulative + state["daily_pnl"], 2),
        "trades_count": len(trades_today),
        "buys": len(buys),
        "sells": len(sells),
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "best_trade_pnl": round(max(today_pnls), 2) if today_pnls else 0.0,
        "worst_trade_pnl": round(min(today_pnls), 2) if today_pnls else 0.0,
        "positions_open": len(state.get("positions", [])),
    }

    # Upsert: update today's entry if it exists, otherwise append
    existing_idx = next(
        (i for i, s in enumerate(summaries) if s["date"] == today), None
    )
    if existing_idx is not None:
        # Recalculate cumulative from previous entry
        if existing_idx > 0:
            entry["cumulative_pnl"] = round(
                summaries[existing_idx - 1]["cumulative_pnl"] + state["daily_pnl"], 2
            )
        else:
            entry["cumulative_pnl"] = round(state["daily_pnl"], 2)
        summaries[existing_idx] = entry
    else:
        summaries.append(entry)

    _save_json(DAILY_SUMMARIES_FILE, summaries)


def save_decisions(decisions: list[dict]) -> None:
    data = {
        "run_time": datetime.now(timezone.utc).isoformat(),
        "decisions": decisions,
    }
    _save_json(LATEST_DECISIONS_FILE, data)

