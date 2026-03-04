import logging
from datetime import datetime, timezone

from bot.config import Config
from bot.market_data import fetch_indicators
from bot.analyst import get_trading_decision
from bot.broker import Trading212Broker
from bot.risk import validate_decision
from bot.state import (
    load_state,
    save_state,
    reset_daily_state,
    get_position,
    add_position,
    remove_position,
    add_trade,
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

    all_decisions: list[dict] = []

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
                add_trade(
                    state,
                    ticker,
                    "SELL",
                    position["quantity"],
                    current_price,
                    "Stop-loss triggered",
                )
                remove_position(state, ticker)
                append_trade(
                    ticker=ticker,
                    yf_symbol=yf_symbol,
                    action="SELL",
                    quantity=position["quantity"],
                    price=current_price,
                    reasoning="Stop-loss triggered",
                    confidence=None,
                    indicators=None,
                    stop_loss=None,
                    take_profit=None,
                    pnl=pnl,
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
                add_trade(
                    state,
                    ticker,
                    "SELL",
                    position["quantity"],
                    current_price,
                    "Take-profit triggered",
                )
                remove_position(state, ticker)
                append_trade(
                    ticker=ticker,
                    yf_symbol=yf_symbol,
                    action="SELL",
                    quantity=position["quantity"],
                    price=current_price,
                    reasoning="Take-profit triggered",
                    confidence=None,
                    indicators=None,
                    stop_loss=None,
                    take_profit=None,
                    pnl=pnl,
                )
            continue

    # --- Step 2: Analyze each stock in watchlist ---
    for t212_ticker, yf_symbol in config.watchlist.items():
        logger.info(f"Analyzing {t212_ticker} ({yf_symbol})...")

        indicators = fetch_indicators(yf_symbol, config.indicator_history_length)
        if not indicators:
            logger.warning(f"Skipping {yf_symbol}: no market data available")
            all_decisions.append(
                {
                    "ticker": t212_ticker,
                    "yf_symbol": yf_symbol,
                    "action": "HOLD",
                    "confidence": 0,
                    "reasoning": "No market data",
                    "was_executed": False,
                    "rejection_reason": "No market data",
                    "indicators": None,
                }
            )
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
            all_decisions.append(
                {
                    "ticker": t212_ticker,
                    "yf_symbol": yf_symbol,
                    "action": "HOLD",
                    "confidence": 0,
                    "reasoning": "Model returned no decision",
                    "was_executed": False,
                    "rejection_reason": "Model error or no response",
                    "indicators": indicators["current"],
                }
            )
            continue

        logger.info(
            f"{t212_ticker}: {decision['action']} "
            f"(confidence: {decision.get('confidence', 'N/A')})"
        )

        # Check for duplicate position before risk validation
        if decision["action"] == "BUY" and current_position is not None:
            logger.info(f"{t212_ticker}: Already holding, skipping BUY")
            all_decisions.append(
                {
                    "ticker": t212_ticker,
                    "yf_symbol": yf_symbol,
                    "action": decision["action"],
                    "confidence": decision["confidence"],
                    "reasoning": decision["reasoning"],
                    "was_executed": False,
                    "rejection_reason": "Already holding position",
                    "indicators": indicators["current"],
                }
            )
            continue

        approved = validate_decision(decision, current_price, state, config)

        if not approved:
            logger.info(f"{t212_ticker}: Decision rejected by risk manager")
            all_decisions.append(
                {
                    "ticker": t212_ticker,
                    "yf_symbol": yf_symbol,
                    "action": decision["action"],
                    "confidence": decision["confidence"],
                    "reasoning": decision["reasoning"],
                    "was_executed": False,
                    "rejection_reason": "Failed risk validation",
                    "indicators": indicators["current"],
                }
            )
            continue

        # --- Execute ---
        executed = False

        if approved["action"] == "BUY":
            result = broker.place_market_order(t212_ticker, approved["quantity"])
            if result:
                executed = True
                add_position(
                    state,
                    t212_ticker,
                    approved["quantity"],
                    current_price,
                    approved["stop_loss"],
                    approved["take_profit"],
                )
                add_trade(
                    state,
                    t212_ticker,
                    "BUY",
                    approved["quantity"],
                    current_price,
                    approved.get("reasoning", ""),
                )
                append_trade(
                    ticker=t212_ticker,
                    yf_symbol=yf_symbol,
                    action="BUY",
                    quantity=approved["quantity"],
                    price=current_price,
                    reasoning=approved.get("reasoning", ""),
                    confidence=approved["confidence"],
                    indicators=indicators["current"],
                    stop_loss=approved["stop_loss"],
                    take_profit=approved["take_profit"],
                    pnl=None,
                )

        elif approved["action"] == "SELL" and current_position:
            result = broker.close_position(t212_ticker, current_position["quantity"])
            if result:
                executed = True
                pnl = round(
                    (current_price - current_position["entry_price"])
                    * current_position["quantity"],
                    2,
                )
                state["daily_pnl"] += pnl
                remove_position(state, t212_ticker)
                add_trade(
                    state,
                    t212_ticker,
                    "SELL",
                    current_position["quantity"],
                    current_price,
                    approved.get("reasoning", ""),
                )
                append_trade(
                    ticker=t212_ticker,
                    yf_symbol=yf_symbol,
                    action="SELL",
                    quantity=current_position["quantity"],
                    price=current_price,
                    reasoning=approved.get("reasoning", ""),
                    confidence=approved["confidence"],
                    indicators=indicators["current"],
                    stop_loss=None,
                    take_profit=None,
                    pnl=pnl,
                )

        all_decisions.append(
            {
                "ticker": t212_ticker,
                "yf_symbol": yf_symbol,
                "action": approved["action"],
                "confidence": approved["confidence"],
                "reasoning": approved["reasoning"],
                "was_executed": executed,
                "rejection_reason": None if executed else "Broker rejected order",
                "indicators": indicators["current"],
            }
        )

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
    logger.info(
        f"Cumulative P&L: ${state['cumulative_pnl']:.2f} "
        f"(peak: ${state['peak_pnl']:.2f}, drawdown: ${drawdown:.2f})"
    )
    logger.info(f"Open positions: {len(state['positions'])}")


if __name__ == "__main__":
    run()

