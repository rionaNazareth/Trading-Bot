# Phase 3 — AI Decision Engine (Gemini Flash)

## Goal

Integrate Google Gemini 2.0 Flash to analyze technical indicators and produce structured buy/sell/hold decisions in JSON format.

## Depends On

- Phase 1: `bot/config.py` (for `gemini_api_key`, risk parameter values)
- Phase 2: `bot/market_data.py` (defines the indicators dict format that this module consumes)

## What the Next Phase Expects

- `bot/analyst.py` exists with a `get_trading_decision(ticker, indicators, current_position, daily_pnl, config) -> dict | None` function
- Returns a dict matching the "Gemini Decision Dict" schema in ARCHITECTURE.md
- Returns `None` on any failure (API error, invalid JSON, etc.)

## Files to Create

### 1. `bot/analyst.py`

```python
import json
import logging

import google.generativeai as genai

from bot.config import Config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a quantitative intraday trading analyst. You analyze technical indicators — both current values AND recent history — to identify trends, divergences, and momentum shifts. You MUST respond with ONLY a valid JSON object, no markdown, no explanation outside the JSON.

Rules you MUST follow:
1. Only recommend BUY if multiple indicators align AND the trend supports it (e.g., RSI trending down to oversold + MACD histogram narrowing/crossing + price near lower Bollinger Band + volume confirming)
2. Only recommend SELL if holding a position AND indicators suggest reversal or momentum loss
3. Default to HOLD if signals are mixed, unclear, or volume does not confirm the move
4. Set confidence between 0.0 and 1.0 — only values >= 0.7 will be acted upon
5. Always suggest a stop_loss and take_profit price. Use the ATR value to set appropriate distances
6. quantity must be a whole number >= 1
7. Consider the daily P&L — if losses are mounting, be more conservative
8. If not holding a position, never recommend SELL
9. Pay attention to the INDICATOR HISTORY — look for divergences (e.g., price making new lows but RSI making higher lows), trend direction, and momentum changes
10. Volume confirmation is critical — a move without volume support is suspect

Response format (JSON only, no markdown fences):
{"action": "BUY|SELL|HOLD", "confidence": 0.0-1.0, "quantity": integer, "reasoning": "string", "stop_loss": float, "take_profit": float}"""

USER_PROMPT_TEMPLATE = """Analyze {ticker} for an intraday trading decision.

CURRENT MARKET DATA:
- Price: ${current_price}
- Volume: {volume}
- RSI(14): {rsi_14}
- MACD: {macd} | Signal: {macd_signal} | Histogram: {macd_histogram}
- Bollinger Bands: Upper={bb_upper} | Middle={bb_middle} | Lower={bb_lower} | %B={bb_pct} | Width={bb_width}
- EMA(9): {ema_9} | EMA(21): {ema_21} | Trend: {ema_trend}
- ATR(14): {atr_14} (volatility measure)
- OBV Trend: {obv_trend} (volume confirmation)
- Price Change: {price_change_pct}%

INDICATOR HISTORY (last {history_length} candles, oldest first):
{indicator_history}

CURRENT POSITION: {position_info}

DAILY P&L: ${daily_pnl}

MAX POSITION VALUE: ${max_position_value}

Analyze the trend in the indicator history. Look for RSI divergence, MACD crossovers, Bollinger squeeze/breakout patterns, and volume confirmation. Respond with JSON only."""


def _format_position_info(position: dict | None) -> str:
    if position is None:
        return "None (not holding)"
    return (
        f"Holding {position['quantity']} shares at entry price "
        f"${position['entry_price']}, stop-loss at ${position['stop_loss']}, "
        f"take-profit at ${position['take_profit']}"
    )


def _clean_json_response(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return text


def _format_history(history: list[dict]) -> str:
    lines = []
    for i, candle in enumerate(history):
        parts = [f"price={candle['price']}"]
        if candle.get("rsi_14") is not None:
            parts.append(f"RSI={candle['rsi_14']}")
        if candle.get("macd_histogram") is not None:
            parts.append(f"MACD_hist={candle['macd_histogram']}")
        if candle.get("bb_pct") is not None:
            parts.append(f"BB%={candle['bb_pct']}")
        if candle.get("ema_9") is not None and candle.get("ema_21") is not None:
            parts.append(f"EMA9={candle['ema_9']}")
            parts.append(f"EMA21={candle['ema_21']}")
        parts.append(f"vol={candle['volume']}")
        lines.append(f"  [{i+1}] {', '.join(parts)}")
    return "\n".join(lines)


def get_trading_decision(
    ticker: str,
    indicators: dict,
    current_position: dict | None,
    daily_pnl: float,
    config: Config,
) -> dict | None:
    try:
        genai.configure(api_key=config.gemini_api_key)
        model = genai.GenerativeModel(
            "gemini-2.0-flash",
            system_instruction=SYSTEM_PROMPT,
        )

        current = indicators["current"]
        history = indicators.get("history", [])

        user_prompt = USER_PROMPT_TEMPLATE.format(
            ticker=ticker,
            current_price=current["current_price"],
            volume=current["volume"],
            rsi_14=current["rsi_14"],
            macd=current["macd"],
            macd_signal=current["macd_signal"],
            macd_histogram=current["macd_histogram"],
            bb_upper=current["bb_upper"],
            bb_middle=current["bb_middle"],
            bb_lower=current["bb_lower"],
            bb_pct=current["bb_pct"],
            bb_width=current.get("bb_width", "N/A"),
            ema_9=current["ema_9"],
            ema_21=current["ema_21"],
            ema_trend=current["ema_trend"],
            atr_14=current.get("atr_14", "N/A"),
            obv_trend=current.get("obv_trend", "N/A"),
            price_change_pct=current["price_change_pct"],
            history_length=len(history),
            indicator_history=_format_history(history),
            position_info=_format_position_info(current_position),
            daily_pnl=daily_pnl,
            max_position_value=config.max_position_value,
        )

        response = model.generate_content(user_prompt)
        raw_text = response.text
        cleaned = _clean_json_response(raw_text)
        decision = json.loads(cleaned)

        required_keys = {"action", "confidence", "quantity", "reasoning", "stop_loss", "take_profit"}
        if not required_keys.issubset(decision.keys()):
            missing = required_keys - decision.keys()
            logger.warning(f"{ticker}: Gemini response missing keys: {missing}")
            return None

        if decision["action"] not in ("BUY", "SELL", "HOLD"):
            logger.warning(f"{ticker}: Invalid action '{decision['action']}'")
            return None

        decision["confidence"] = float(decision["confidence"])
        decision["quantity"] = int(decision["quantity"])
        decision["stop_loss"] = float(decision["stop_loss"])
        decision["take_profit"] = float(decision["take_profit"])

        return decision

    except json.JSONDecodeError as e:
        logger.error(f"{ticker}: Failed to parse Gemini response as JSON: {e}")
        logger.debug(f"{ticker}: Raw response: {raw_text}")
        return None
    except Exception as e:
        logger.error(f"{ticker}: Gemini API call failed: {e}")
        return None
```

Implementation notes:
- `SYSTEM_PROMPT` and `USER_PROMPT_TEMPLATE` are exact — do not modify them
- `_clean_json_response` strips markdown fences in case Gemini wraps its JSON in ```
- All required fields are validated after parsing
- Type coercion (`float()`, `int()`) ensures consistent types even if Gemini returns strings
- `genai.configure()` is called each time — this is safe and idempotent
- The function NEVER raises — all errors are caught, logged, and return `None`

## Verification

Requires a Gemini API key. Create `.env` with `GEMINI_API_KEY`, then:

```bash
python -c "
from bot.config import Config
from bot.analyst import get_trading_decision

c = Config.from_env()

sample_indicators = {
    'current': {
        'symbol': 'AAPL', 'current_price': 185.0, 'volume': 50000000,
        'rsi_14': 28.0, 'macd': -0.82, 'macd_signal': -0.45, 'macd_histogram': -0.37,
        'bb_upper': 190.0, 'bb_middle': 185.0, 'bb_lower': 180.0, 'bb_pct': 0.12,
        'bb_width': 0.054, 'ema_9': 184.0, 'ema_21': 186.0, 'ema_trend': 'bearish',
        'atr_14': 1.85, 'obv_trend': 'falling', 'price_change_pct': -0.8,
    },
    'history': [
        {'price': 188.0, 'volume': 48000000, 'rsi_14': 52.0, 'macd_histogram': 0.15, 'bb_pct': 0.65, 'ema_9': 187.5, 'ema_21': 186.8},
        {'price': 187.2, 'volume': 45000000, 'rsi_14': 45.0, 'macd_histogram': 0.02, 'bb_pct': 0.52, 'ema_9': 187.0, 'ema_21': 186.7},
        {'price': 186.1, 'volume': 51000000, 'rsi_14': 38.0, 'macd_histogram': -0.18, 'bb_pct': 0.35, 'ema_9': 186.2, 'ema_21': 186.5},
        {'price': 185.5, 'volume': 49000000, 'rsi_14': 32.0, 'macd_histogram': -0.28, 'bb_pct': 0.22, 'ema_9': 185.5, 'ema_21': 186.3},
        {'price': 185.0, 'volume': 50000000, 'rsi_14': 28.0, 'macd_histogram': -0.37, 'bb_pct': 0.12, 'ema_9': 184.0, 'ema_21': 186.0},
    ],
}

decision = get_trading_decision('AAPL_US_EQ', sample_indicators, None, 0.0, c)
if decision:
    for k, v in decision.items():
        print(f'  {k}: {v}')
    print('Phase 3 PASSED')
else:
    print('No decision returned (check logs)')
"
```

Expected output (values will vary — Gemini's response is non-deterministic):
```
  action: BUY
  confidence: 0.75
  quantity: 3
  reasoning: RSI at 28 indicates oversold condition...
  stop_loss: 179.5
  take_profit: 194.25
  Phase 3 PASSED
```

The model may return HOLD if it deems the signals insufficient. That's fine — it means the prompt is working correctly.
