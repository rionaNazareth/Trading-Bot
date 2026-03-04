# Phase 4 — Risk Management, Data Export, and Orchestrator

## Goal

Wire everything together. After this phase, the bot runs end-to-end locally: it fetches data, calls Gemini, validates risk, executes trades, and saves state + dashboard data files.

## Depends On

- Phase 1: `bot/config.py`, `bot/broker.py`, `bot/state.py`
- Phase 2: `bot/market_data.py`
- Phase 3: `bot/analyst.py`

## What the Next Phase Expects

- `bot/risk.py` exists with `validate_decision()` that enforces all safety checks
- `bot/data_export.py` exists and writes to `data/trades.json`, `data/daily_summaries.json`, `data/latest_decisions.json`
- `bot/main.py` exists and can be run with `python -m bot.main`
- After a run: `state.json` is updated, `data/` files are populated

## Files to Create

### 1. `bot/risk.py`

```python
import logging

from bot.config import Config

logger = logging.getLogger(__name__)


def validate_decision(
    decision: dict,
    current_price: float,
    state: dict,
    config: Config,
) -> dict | None:
    action = decision.get("action")

    # Check 1: Valid action
    if action not in ("BUY", "SELL"):
        if action == "HOLD":
            logger.info("Decision is HOLD — no action needed")
        else:
            logger.warning(f"Invalid action: {action}")
        return None

    # Check 2: Confidence threshold
    confidence = decision.get("confidence", 0)
    if confidence < config.confidence_threshold:
        logger.info(f"Confidence {confidence} below threshold {config.confidence_threshold}")
        return None

    # Check 3: Daily loss limit (block BUYs, allow SELLs to close positions)
    if action == "BUY" and state["daily_pnl"] <= config.max_daily_loss:
        logger.warning(f"Daily loss limit reached ({state['daily_pnl']}). Blocking BUY.")
        return None

    # Check 3b: Max cumulative drawdown from peak
    cumulative_pnl = state.get("cumulative_pnl", 0)
    peak_pnl = state.get("peak_pnl", 0)
    drawdown = cumulative_pnl - peak_pnl
    if action == "BUY" and drawdown <= config.max_drawdown:
        logger.warning(f"Max drawdown reached (cumulative={cumulative_pnl}, peak={peak_pnl}, drawdown={drawdown}). Blocking BUY.")
        return None

    # Check 4: Max open positions
    if action == "BUY" and len(state["positions"]) >= config.max_open_positions:
        logger.info(f"Max open positions ({config.max_open_positions}) reached. Blocking BUY.")
        return None

    # Check 5: Position size — reduce quantity if needed
    if action == "BUY":
        max_quantity = int(config.max_position_value / current_price)
        if max_quantity < 1:
            logger.info(f"Price ${current_price} exceeds max position value ${config.max_position_value}")
            return None
        if decision["quantity"] > max_quantity:
            logger.info(f"Reducing quantity from {decision['quantity']} to {max_quantity}")
            decision["quantity"] = max_quantity

    # Check 6: No duplicate positions
    if action == "BUY":
        held_tickers = {p["ticker"] for p in state["positions"]}
        # Ticker is not in this dict directly, but caller passes the right context
        # This check is done in main.py before calling validate_decision

    # Check 7: Ensure stop-loss exists
    if not decision.get("stop_loss"):
        decision["stop_loss"] = round(current_price * (1 - config.default_stop_loss_pct), 2)
        logger.info(f"No stop_loss from model, defaulting to {decision['stop_loss']}")

    # Check 8: Ensure take-profit exists
    if not decision.get("take_profit"):
        decision["take_profit"] = round(current_price * (1 + config.default_take_profit_pct), 2)
        logger.info(f"No take_profit from model, defaulting to {decision['take_profit']}")

    return decision
```

### 2. `bot/data_export.py`

```python
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

    trades.append({
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
    })

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
    today_pnls = [t["pnl"] for t in all_trades
                  if t.get("time", "").startswith(today) and t.get("pnl") is not None]

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
```

### 3. `bot/main.py`

```python
import logging
from datetime import datetime, timezone

from bot.config import Config
from bot.market_data import fetch_indicators
from bot.analyst import get_trading_decision
from bot.broker import Trading212Broker
from bot.risk import validate_decision
from bot.state import (
    load_state, save_state, reset_daily_state,
    get_position, add_position, remove_position, add_trade,
)
from bot.data_export import append_trade, update_daily_summary, save_decisions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def run():
    config = Config.from_env()
    state = load_state()
    state = reset_daily_state(state)
    broker = Trading212Broker(
        config.t212_api_key, config.t212_api_secret, config.t212_environment
    )

    all_decisions = []

    # --- Step 1: Check stop-loss / take-profit for existing positions ---
    for position in list(state["positions"]):
        ticker = position["ticker"]
        yf_symbol = config.watchlist.get(ticker)
        if not yf_symbol:
            continue

        indicators = fetch_indicators(yf_symbol, config.indicator_history_length)
        if not indicators:
            continue

        current_price = indicators["current"]["current_price"]

        # Stop-loss check
        if current_price <= position["stop_loss"]:
            logger.info(f"STOP-LOSS hit for {ticker} at ${current_price}")
            result = broker.close_position(ticker, position["quantity"])
            if result:
                pnl = round(
                    (current_price - position["entry_price"]) * position["quantity"], 2
                )
                state["daily_pnl"] += pnl
                add_trade(state, ticker, "SELL", position["quantity"], current_price,
                         "Stop-loss triggered")
                remove_position(state, ticker)
                append_trade(
                    ticker=ticker, yf_symbol=yf_symbol, action="SELL",
                    quantity=position["quantity"], price=current_price,
                    reasoning="Stop-loss triggered", confidence=None,
                    indicators=None, stop_loss=None, take_profit=None, pnl=pnl,
                )
            continue

        # Take-profit check
        if current_price >= position["take_profit"]:
            logger.info(f"TAKE-PROFIT hit for {ticker} at ${current_price}")
            result = broker.close_position(ticker, position["quantity"])
            if result:
                pnl = round(
                    (current_price - position["entry_price"]) * position["quantity"], 2
                )
                state["daily_pnl"] += pnl
                add_trade(state, ticker, "SELL", position["quantity"], current_price,
                         "Take-profit triggered")
                remove_position(state, ticker)
                append_trade(
                    ticker=ticker, yf_symbol=yf_symbol, action="SELL",
                    quantity=position["quantity"], price=current_price,
                    reasoning="Take-profit triggered", confidence=None,
                    indicators=None, stop_loss=None, take_profit=None, pnl=pnl,
                )
            continue

    # --- Step 2: Analyze each stock in watchlist ---
    for t212_ticker, yf_symbol in config.watchlist.items():
        logger.info(f"Analyzing {t212_ticker} ({yf_symbol})...")

        indicators = fetch_indicators(yf_symbol, config.indicator_history_length)
        if not indicators:
            logger.warning(f"Skipping {yf_symbol}: no market data available")
            all_decisions.append({
                "ticker": t212_ticker, "yf_symbol": yf_symbol,
                "action": "HOLD", "confidence": 0, "reasoning": "No market data",
                "was_executed": False, "rejection_reason": "No market data",
                "indicators": None,
            })
            continue

        current_position = get_position(state, t212_ticker)
        current_price = indicators["current"]["current_price"]

        decision = get_trading_decision(
            ticker=t212_ticker,
            indicators=indicators,
            current_position=current_position,
            daily_pnl=state["daily_pnl"],
            config=config,
        )

        if not decision:
            logger.info(f"{t212_ticker}: No decision from model")
            all_decisions.append({
                "ticker": t212_ticker, "yf_symbol": yf_symbol,
                "action": "HOLD", "confidence": 0, "reasoning": "Model returned no decision",
                "was_executed": False, "rejection_reason": "Model error or no response",
                "indicators": indicators["current"],
            })
            continue

        logger.info(
            f"{t212_ticker}: {decision['action']} "
            f"(confidence: {decision.get('confidence', 'N/A')})"
        )

        # Check for duplicate position before risk validation
        rejection_reason = None
        if decision["action"] == "BUY" and current_position is not None:
            rejection_reason = "Already holding position"
            logger.info(f"{t212_ticker}: Already holding, skipping BUY")
            decision_record = {
                "ticker": t212_ticker, "yf_symbol": yf_symbol,
                "action": decision["action"], "confidence": decision["confidence"],
                "reasoning": decision["reasoning"],
                "was_executed": False, "rejection_reason": rejection_reason,
                "indicators": indicators["current"],
            }
            all_decisions.append(decision_record)
            continue

        approved = validate_decision(decision, current_price, state, config)

        if not approved:
            logger.info(f"{t212_ticker}: Decision rejected by risk manager")
            all_decisions.append({
                "ticker": t212_ticker, "yf_symbol": yf_symbol,
                "action": decision["action"], "confidence": decision["confidence"],
                "reasoning": decision["reasoning"],
                "was_executed": False, "rejection_reason": "Failed risk validation",
                "indicators": indicators["current"],
            })
            continue

        # --- Execute ---
        executed = False

        if approved["action"] == "BUY":
            result = broker.place_market_order(t212_ticker, approved["quantity"])
            if result:
                executed = True
                add_position(
                    state, t212_ticker, approved["quantity"], current_price,
                    approved["stop_loss"], approved["take_profit"],
                )
                add_trade(
                    state, t212_ticker, "BUY", approved["quantity"],
                    current_price, approved.get("reasoning", ""),
                )
                append_trade(
                    ticker=t212_ticker, yf_symbol=yf_symbol, action="BUY",
                    quantity=approved["quantity"], price=current_price,
                    reasoning=approved.get("reasoning", ""),
                    confidence=approved["confidence"], indicators=indicators["current"],
                    stop_loss=approved["stop_loss"],
                    take_profit=approved["take_profit"], pnl=None,
                )

        elif approved["action"] == "SELL" and current_position:
            result = broker.close_position(t212_ticker, current_position["quantity"])
            if result:
                executed = True
                pnl = round(
                    (current_price - current_position["entry_price"])
                    * current_position["quantity"], 2
                )
                state["daily_pnl"] += pnl
                remove_position(state, t212_ticker)
                add_trade(
                    state, t212_ticker, "SELL", current_position["quantity"],
                    current_price, approved.get("reasoning", ""),
                )
                append_trade(
                    ticker=t212_ticker, yf_symbol=yf_symbol, action="SELL",
                    quantity=current_position["quantity"], price=current_price,
                    reasoning=approved.get("reasoning", ""),
                    confidence=approved["confidence"], indicators=indicators["current"],
                    stop_loss=None, take_profit=None, pnl=pnl,
                )

        all_decisions.append({
            "ticker": t212_ticker, "yf_symbol": yf_symbol,
            "action": approved["action"], "confidence": approved["confidence"],
            "reasoning": approved["reasoning"],
            "was_executed": executed,
            "rejection_reason": None if executed else "Broker rejected order",
            "indicators": indicators["current"],
        })

    # --- Step 3: Update cumulative P&L tracking and save ---
    state["cumulative_pnl"] = state.get("cumulative_pnl", 0) + state["daily_pnl"]
    if state["cumulative_pnl"] > state.get("peak_pnl", 0):
        state["peak_pnl"] = state["cumulative_pnl"]

    state["last_run"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    save_decisions(all_decisions)
    update_daily_summary(state)

    drawdown = state["cumulative_pnl"] - state["peak_pnl"]
    logger.info(f"Run complete. Daily P&L: ${state['daily_pnl']:.2f}")
    logger.info(f"Cumulative P&L: ${state['cumulative_pnl']:.2f} (peak: ${state['peak_pnl']:.2f}, drawdown: ${drawdown:.2f})")
    logger.info(f"Open positions: {len(state['positions'])}")


if __name__ == "__main__":
    run()
```

## Verification

With `.env` configured (Trading212 demo + Gemini API key):

```bash
python -m bot.main
```

Expected output (log lines):
```
2026-02-26 15:00:01 [INFO] New trading day: 2026-02-26, daily state reset
2026-02-26 15:00:02 [INFO] Analyzing AAPL_US_EQ (AAPL)...
2026-02-26 15:00:04 [INFO] AAPL_US_EQ: HOLD (confidence: 0.45)
2026-02-26 15:00:04 [INFO] Decision is HOLD — no action needed
2026-02-26 15:00:05 [INFO] Analyzing MSFT_US_EQ (MSFT)...
...
2026-02-26 15:00:10 [INFO] Run complete. Daily P&L: $0.00
2026-02-26 15:00:10 [INFO] Open positions: 0
```

Then verify the data files were updated:

```bash
cat state.json          # last_run should be set
cat data/latest_decisions.json  # should have decisions for all watchlist stocks
cat data/daily_summaries.json   # should have today's entry
```

If the model returns HOLD for everything, that's correct behavior — it means the indicators didn't trigger a strong signal. The bot is working as designed.
