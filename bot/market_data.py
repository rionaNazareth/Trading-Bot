import logging

import ta
import yfinance as yf

logger = logging.getLogger(__name__)


def fetch_indicators(yf_symbol: str, history_length: int = 10) -> dict | None:
    try:
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period="5d", interval="30m")

        if df.empty or len(df) < 26:
            logger.warning(f"{yf_symbol}: Not enough data (got {len(df)} rows, need 26+)")
            return None

        close = df["Close"]
        volume = df["Volume"]

        # Compute indicator series
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
        atr = ta.volatility.AverageTrueRange(
            df["High"], df["Low"], close, window=14
        ).average_true_range()

        # Current values (latest candle)
        prev_close = float(close.iloc[-2])
        current_price = float(close.iloc[-1])
        price_change_pct = round(((current_price - prev_close) / prev_close) * 100, 2)

        ema_9_val = float(ema_9.iloc[-1])
        ema_21_val = float(ema_21.iloc[-1])

        # OBV trend: compare current OBV to OBV 5 candles ago
        obv_now = float(obv.iloc[-1])
        obv_prev = float(obv.iloc[-6]) if len(obv) >= 6 else obv_now
        obv_trend = "rising" if obv_now > obv_prev else "falling"

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
            "obv_trend": obv_trend,
            "price_change_pct": price_change_pct,
        }

        # Historical indicator values (last N candles for trend analysis)
        history: list[dict] = []
        start_idx = max(0, len(df) - history_length)
        for i in range(start_idx, len(df)):
            history.append(
                {
                    "price": round(float(close.iloc[i]), 2),
                    "volume": int(volume.iloc[i]),
                    "rsi_14": round(float(rsi.iloc[i]), 2) if not rsi.isna().iloc[i] else None,
                    "macd": round(float(macd_line.iloc[i]), 4)
                    if not macd_line.isna().iloc[i]
                    else None,
                    "macd_histogram": round(float(macd_hist.iloc[i]), 4)
                    if not macd_hist.isna().iloc[i]
                    else None,
                    "bb_pct": round(float(bb_pct.iloc[i]), 4)
                    if not bb_pct.isna().iloc[i]
                    else None,
                    "ema_9": round(float(ema_9.iloc[i]), 2)
                    if not ema_9.isna().iloc[i]
                    else None,
                    "ema_21": round(float(ema_21.iloc[i]), 2)
                    if not ema_21.isna().iloc[i]
                    else None,
                }
            )

        return {
            "current": current,
            "history": history,
        }

    except Exception as e:
        logger.error(f"Failed to fetch indicators for {yf_symbol}: {e}")
        return None

