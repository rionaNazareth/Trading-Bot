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
        logger.warning(
            f"Max drawdown reached (cumulative={cumulative_pnl}, peak={peak_pnl}, "
            f"drawdown={drawdown}). Blocking BUY."
        )
        return None

    # Check 4: Max open positions
    if action == "BUY" and len(state["positions"]) >= config.max_open_positions:
        logger.info(
            f"Max open positions ({config.max_open_positions}) reached. Blocking BUY."
        )
        return None

    # Check 5: Position size — reduce quantity if needed
    if action == "BUY":
        max_quantity = int(config.max_position_value / current_price)
        if max_quantity < 1:
            logger.info(
                f"Price ${current_price} exceeds max position value "
                f"${config.max_position_value}"
            )
            return None
        if decision["quantity"] > max_quantity:
            logger.info(f"Reducing quantity from {decision['quantity']} to {max_quantity}")
            decision["quantity"] = max_quantity

    # Check 6: No duplicate positions (enforced in main before calling this)

    # Check 7: Ensure stop-loss exists
    if not decision.get("stop_loss"):
        decision["stop_loss"] = round(
            current_price * (1 - config.default_stop_loss_pct), 2
        )
        logger.info(f"No stop_loss from model, defaulting to {decision['stop_loss']}")

    # Check 8: Ensure take-profit exists
    if not decision.get("take_profit"):
        decision["take_profit"] = round(
            current_price * (1 + config.default_take_profit_pct), 2
        )
        logger.info(
            f"No take_profit from model, defaulting to {decision['take_profit']}"
        )

    return decision

