# Phase 4b — Simple Backtesting (Optional but Recommended)

## Goal

Validate the trading strategy on historical data before risking real or demo capital. This phase creates a backtesting module that replays past market data through the same Gemini decision engine and risk management pipeline, producing performance metrics.

This phase was added based on expert trader review: **"Without backtests, you cannot know if the strategy has any edge."**

## Depends On

- Phase 2: `bot/market_data.py` (for indicator computation)
- Phase 3: `bot/analyst.py` (for Gemini decisions)
- Phase 4: `bot/risk.py` (for risk validation)

## What the Next Phase Expects

- `bot/backtest.py` exists with a `run_backtest()` function
- Running it produces a `data/backtest_results.json` with performance metrics
- This is a standalone module — it does NOT affect the live bot

## Why This Matters

- Demonstrates rigor and quantitative thinking (strong resume signal)
- Answers the question: "Does this approach actually work?"
- Identifies whether Gemini's decisions are better than random or buy-and-hold
- Provides baseline metrics to compare against live performance

## Files to Create

### 1. `bot/backtest.py`

```python
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

from bot.config import Config
from bot.market_data import fetch_indicators
from bot.analyst import get_trading_decision
from bot.risk import validate_decision

logger = logging.getLogger(__name__)

BACKTEST_RESULTS_FILE = Path("data/backtest_results.json")


def run_backtest(
    symbols: dict[str, str] | None = None,
    period: str = "1mo",
    interval: str = "30m",
):
    """
    Run a simple walk-forward backtest using historical data.

    Instead of replaying candle-by-candle (which would require thousands of
    Gemini API calls), this backtest:
    1. Fetches historical data for the past month
    2. Splits it into overlapping windows of 30 candles
    3. For each window, computes indicators and asks Gemini for a decision
    4. Simulates the trade by checking the NEXT candle's price movement
    5. Aggregates results into performance metrics

    This is a simplified backtest — not a full event-driven simulation.
    """
    config = Config.from_env()
    if symbols is None:
        symbols = config.watchlist

    all_trades = []
    total_pnl = 0.0

    for t212_ticker, yf_symbol in symbols.items():
        logger.info(f"Backtesting {yf_symbol}...")

        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period=period, interval=interval)

        if df.empty or len(df) < 40:
            logger.warning(f"{yf_symbol}: Not enough historical data")
            continue

        # Sample every 5th candle to stay within Gemini free tier limits
        # (~30 trading days * 15 candles/day / 5 = ~90 calls per symbol)
        sample_points = list(range(30, len(df) - 1, 5))

        for idx in sample_points:
            window_df = df.iloc[:idx + 1]
            close = window_df["Close"]
            next_price = float(df["Close"].iloc[idx + 1])

            # Use the market_data module to compute indicators on this window
            # Note: fetch_indicators fetches live data; for backtest we need
            # to compute indicators directly on the historical DataFrame.
            # Reuse the ta library computations inline:
            indicators = _compute_indicators_from_df(window_df, yf_symbol)
            if indicators is None:
                continue

            current_price = indicators["current"]["current_price"]

            # Get Gemini's decision
            decision = get_trading_decision(
                ticker=t212_ticker,
                indicators=indicators,
                current_position=None,
                daily_pnl=0.0,
                config=config,
            )

            if not decision or decision["action"] != "BUY":
                continue

            # Simulate: if BUY, check next candle
            simulated_pnl = round((next_price - current_price) * decision["quantity"], 2)
            total_pnl += simulated_pnl

            all_trades.append({
                "symbol": yf_symbol,
                "action": "BUY",
                "entry_price": current_price,
                "exit_price": next_price,
                "quantity": decision["quantity"],
                "pnl": simulated_pnl,
                "confidence": decision["confidence"],
                "reasoning": decision["reasoning"],
            })

    # Compute metrics
    wins = [t for t in all_trades if t["pnl"] > 0]
    losses = [t for t in all_trades if t["pnl"] <= 0]
    win_rate = len(wins) / len(all_trades) if all_trades else 0
    avg_profit = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["pnl"] for t in losses) / len(losses) if losses else 0

    results = {
        "run_date": datetime.now(timezone.utc).isoformat(),
        "period": period,
        "symbols_tested": list(symbols.values()),
        "total_trades": len(all_trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 4),
        "total_pnl": round(total_pnl, 2),
        "avg_profit": round(avg_profit, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(abs(avg_profit / avg_loss), 2) if avg_loss != 0 else None,
        "trades": all_trades,
    }

    BACKTEST_RESULTS_FILE.write_text(json.dumps(results, indent=2))
    logger.info(f"Backtest complete: {len(all_trades)} trades, win rate {win_rate:.1%}, total P&L ${total_pnl:.2f}")

    return results


def _compute_indicators_from_df(df, yf_symbol, history_length=10):
    """Compute indicators from a DataFrame slice (same logic as market_data.py but on provided data)."""
    import ta

    if len(df) < 26:
        return None

    close = df["Close"]
    volume = df["Volume"]

    rsi = ta.momentum.RSIIndicator(close, window=14).rsi()
    macd_ind = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
    macd_line = macd_ind.macd()
    macd_signal = macd_ind.macd_signal()
    macd_hist = macd_ind.macd_diff()
    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    bb_pct = bb.bollinger_pband()
    bb_width = bb.bollinger_wband()
    ema_9 = ta.trend.EMAIndicator(close, window=9).ema_indicator()
    ema_21 = ta.trend.EMAIndicator(close, window=21).ema_indicator()
    obv = ta.volume.OnBalanceVolumeIndicator(close, volume).on_balance_volume()
    atr = ta.volatility.AverageTrueRange(df["High"], df["Low"], close, window=14).average_true_range()

    ema_9_val = float(ema_9.iloc[-1])
    ema_21_val = float(ema_21.iloc[-1])
    current_price = float(close.iloc[-1])
    prev_close = float(close.iloc[-2])
    obv_now = float(obv.iloc[-1])
    obv_prev = float(obv.iloc[-6]) if len(obv) >= 6 else obv_now

    current = {
        "symbol": yf_symbol,
        "current_price": current_price,
        "volume": int(volume.iloc[-1]),
        "rsi_14": round(float(rsi.iloc[-1]), 2),
        "macd": round(float(macd_line.iloc[-1]), 4),
        "macd_signal": round(float(macd_signal.iloc[-1]), 4),
        "macd_histogram": round(float(macd_hist.iloc[-1]), 4),
        "bb_upper": round(float(bb.bollinger_hband().iloc[-1]), 2),
        "bb_middle": round(float(bb.bollinger_mavg().iloc[-1]), 2),
        "bb_lower": round(float(bb.bollinger_lband().iloc[-1]), 2),
        "bb_pct": round(float(bb_pct.iloc[-1]), 4),
        "bb_width": round(float(bb_width.iloc[-1]), 4),
        "ema_9": round(ema_9_val, 2),
        "ema_21": round(ema_21_val, 2),
        "ema_trend": "bullish" if ema_9_val > ema_21_val else "bearish",
        "atr_14": round(float(atr.iloc[-1]), 4),
        "obv_trend": "rising" if obv_now > obv_prev else "falling",
        "price_change_pct": round(((current_price - prev_close) / prev_close) * 100, 2),
    }

    history = []
    start_idx = max(0, len(df) - history_length)
    for i in range(start_idx, len(df)):
        history.append({
            "price": round(float(close.iloc[i]), 2),
            "volume": int(volume.iloc[i]),
            "rsi_14": round(float(rsi.iloc[i]), 2) if not rsi.isna().iloc[i] else None,
            "macd_histogram": round(float(macd_hist.iloc[i]), 4) if not macd_hist.isna().iloc[i] else None,
            "bb_pct": round(float(bb_pct.iloc[i]), 4) if not bb_pct.isna().iloc[i] else None,
            "ema_9": round(float(ema_9.iloc[i]), 2) if not ema_9.isna().iloc[i] else None,
            "ema_21": round(float(ema_21.iloc[i]), 2) if not ema_21.isna().iloc[i] else None,
        })

    return {"current": current, "history": history}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    results = run_backtest()
    print(f"\nTotal trades: {results['total_trades']}")
    print(f"Win rate: {results['win_rate']:.1%}")
    print(f"Total P&L: ${results['total_pnl']:.2f}")
    print(f"Profit factor: {results['profit_factor']}")
```

## Important Notes

- **Gemini API usage**: The backtest samples every 5th candle to avoid hitting the free tier limit (1,500 req/day). For 5 symbols over 1 month, expect ~400-500 API calls per backtest run.
- **Simplified simulation**: This is a walk-forward test, not a full event-driven simulation. It asks "if Gemini said BUY at candle N, what happened at candle N+1?" It does not simulate holding periods, stop-losses over multiple candles, or portfolio effects.
- **Run sparingly**: Don't run this on every CI run. Run it manually when tuning the prompt or watchlist.
- **Interpret results carefully**: If win rate < 50% or profit factor < 1.0, the strategy has no edge and should not be used with real money.

## Verification

```bash
# Requires GEMINI_API_KEY in .env
python -m bot.backtest
```

Expected output:
```
2026-02-26 15:00:01 [INFO] Backtesting AAPL...
2026-02-26 15:00:30 [INFO] Backtesting JPM...
...
2026-02-26 15:02:00 [INFO] Backtest complete: 23 trades, win rate 52.2%, total P&L $14.30

Total trades: 23
Win rate: 52.2%
Total P&L: $14.30
Profit factor: 1.35
```

Then check the results:
```bash
cat data/backtest_results.json | python -m json.tool | head -20
```

## Interpreting Results

| Metric | Good | Bad | Action |
|--------|------|-----|--------|
| Win rate | > 50% | < 45% | Tune Gemini prompt or indicators |
| Profit factor | > 1.2 | < 1.0 | Strategy has no edge, do not use with real money |
| Total P&L | Positive | Negative | Review losing trades' reasoning |
| Avg profit vs avg loss | Avg profit > avg loss | Avg loss > avg profit | Tighten stop-loss or improve entry signals |
