# Phase 1 — Project Setup, Config, Broker, State

## Goal

Create a runnable Python project that can authenticate with Trading212, manage persistent state, and serve as the foundation for all subsequent phases.

## Depends On

Nothing — this is the first phase.

## What the Next Phase Expects

- `bot/config.py` exists with a `Config` dataclass that loads from environment variables
- `bot/broker.py` exists with a `Trading212Broker` class that can make authenticated API calls
- `bot/state.py` exists with functions to load/save `state.json` and manage positions
- `requirements.txt` has all Python dependencies
- `.env.example` documents required environment variables

## Files to Create

### 1. `requirements.txt`

```
yfinance>=0.2.36
ta>=0.11.0
google-generativeai>=0.8.0
httpx>=0.27.0
python-dotenv>=1.0.0
```

### 2. `.env.example`

```
TRADING212_API_KEY=<your API key ID>
TRADING212_API_SECRET=<your API secret>
TRADING212_ENVIRONMENT=demo
GEMINI_API_KEY=<your Gemini API key from https://aistudio.google.com/apikey>
```

### 3. `.gitignore`

```
__pycache__/
*.pyc
.env
.venv/
venv/
node_modules/
dashboard/dist/
```

Do NOT gitignore `state.json` or `data/` — they must be committed to persist between runs.

### 4. `bot/__init__.py`

Empty file. Makes `bot/` a Python package so we can run `python -m bot.main`.

### 5. `bot/config.py`

```python
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    t212_api_key: str
    t212_api_secret: str
    t212_environment: str
    gemini_api_key: str

    # Diversified across sectors to avoid correlated positions
    watchlist: dict[str, str] = field(default_factory=lambda: {
        "AAPL_US_EQ": "AAPL",     # Tech
        "JPM_US_EQ": "JPM",       # Finance
        "XOM_US_EQ": "XOM",       # Energy
        "JNJ_US_EQ": "JNJ",       # Healthcare
        "WMT_US_EQ": "WMT",       # Consumer
    })

    max_position_value: float = 100.0
    max_open_positions: int = 3
    max_daily_loss: float = -50.0
    max_drawdown: float = -150.0       # max cumulative loss from peak before halting all trading
    confidence_threshold: float = 0.7
    default_stop_loss_pct: float = 0.03
    default_take_profit_pct: float = 0.05
    indicator_history_length: int = 10  # number of recent candles to send to Gemini

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            t212_api_key=os.environ["TRADING212_API_KEY"],
            t212_api_secret=os.environ["TRADING212_API_SECRET"],
            t212_environment=os.getenv("TRADING212_ENVIRONMENT", "demo"),
            gemini_api_key=os.environ["GEMINI_API_KEY"],
        )
```

Field reference:
- `watchlist`: Maps Trading212 ticker to yfinance symbol. Diversified across sectors (tech, finance, energy, healthcare, consumer) to avoid correlated positions — 3 tech stocks was flagged as a single large bet on one sector
- `max_position_value`: Maximum EUR value per position (default 100)
- `max_open_positions`: Max simultaneous positions (default 3)
- `max_daily_loss`: Stop all buying if daily P&L drops below this (default -50 EUR)
- `max_drawdown`: Stop ALL trading if cumulative P&L from peak drops below this (default -150 EUR). Prevents slow bleed over multiple days
- `confidence_threshold`: Only act on Gemini decisions with confidence >= this (default 0.7)
- `default_stop_loss_pct`: Default stop-loss percentage if model doesn't suggest one (default 3%)
- `default_take_profit_pct`: Default take-profit percentage (default 5%)
- `indicator_history_length`: Number of recent candles (with indicator values) to send to Gemini for trend/divergence analysis (default 10)

### 6. `bot/broker.py`

```python
import base64
import logging

import httpx

logger = logging.getLogger(__name__)


class Trading212Broker:
    def __init__(self, api_key: str, api_secret: str, environment: str = "demo"):
        credentials = base64.b64encode(
            f"{api_key}:{api_secret}".encode("utf-8")
        ).decode("utf-8")
        self.base_url = f"https://{environment}.trading212.com/api/v0"
        self.headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> dict | list | None:
        try:
            response = httpx.request(
                method, f"{self.base_url}{path}", headers=self.headers, **kwargs
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} on {method} {path}: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Request failed for {method} {path}: {e}")
            return None

    def get_open_positions(self) -> list[dict]:
        result = self._request("GET", "/equity/portfolio")
        return result if isinstance(result, list) else []

    def get_account_cash(self) -> dict | None:
        return self._request("GET", "/equity/account/cash")

    def place_market_order(self, ticker: str, quantity: int) -> dict | None:
        return self._request(
            "POST", "/equity/orders/market",
            json={"ticker": ticker, "quantity": quantity},
        )

    def close_position(self, ticker: str, quantity: int) -> dict | None:
        return self._request(
            "POST", "/equity/orders/market",
            json={"ticker": ticker, "quantity": -quantity},
        )

    def place_limit_order(self, ticker: str, quantity: int,
                          limit_price: float, stop_price: float | None = None,
                          take_profit: float | None = None) -> dict | None:
        payload = {
            "ticker": ticker,
            "quantity": quantity,
            "limitPrice": limit_price,
        }
        if stop_price is not None:
            payload["stopPrice"] = stop_price
        if take_profit is not None:
            payload["takeProfitPrice"] = take_profit
        return self._request("POST", "/equity/orders/limit", json=payload)

    def place_stop_order(self, ticker: str, quantity: int,
                         stop_price: float) -> dict | None:
        return self._request(
            "POST", "/equity/orders/stop",
            json={"ticker": ticker, "quantity": quantity, "stopPrice": stop_price},
        )
```

Implementation notes:
- All methods return `None` on any failure — the caller (main.py) handles None gracefully
- `close_position` sells by placing a market order with negative quantity
- `_request` logs the HTTP status and response body on errors
- `_request` includes retry logic (3 attempts with 1s backoff) for transient network errors
- `place_limit_order` and `place_stop_order` allow the bot to use Trading212's native stop-loss/take-profit instead of polling every 30 minutes. The orchestrator should prefer these when available

### 7. `bot/state.py`

```python
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


def add_position(state: dict, ticker: str, quantity: int, price: float,
                 stop_loss: float, take_profit: float) -> dict:
    state["positions"].append({
        "ticker": ticker,
        "quantity": quantity,
        "entry_price": price,
        "entry_time": datetime.now(timezone.utc).isoformat(),
        "stop_loss": stop_loss,
        "take_profit": take_profit,
    })
    return state


def remove_position(state: dict, ticker: str) -> dict:
    state["positions"] = [p for p in state["positions"] if p["ticker"] != ticker]
    return state


def add_trade(state: dict, ticker: str, action: str, quantity: int,
              price: float, reasoning: str) -> dict:
    state["trade_history"].append({
        "ticker": ticker,
        "action": action,
        "quantity": quantity,
        "price": price,
        "time": datetime.now(timezone.utc).isoformat(),
        "reasoning": reasoning,
    })
    return state
```

### 8. `state.json` (initial — commit to repo root)

```json
{
    "positions": [],
    "daily_pnl": 0.0,
    "trading_day": null,
    "trade_history": [],
    "last_run": null,
    "cumulative_pnl": 0.0,
    "peak_pnl": 0.0
}
```

### 9. `data/` directory — initial files

Create these three files:

**`data/trades.json`**:
```json
[]
```

**`data/daily_summaries.json`**:
```json
[]
```

**`data/latest_decisions.json`**:
```json
{
    "run_time": null,
    "decisions": []
}
```

## Verification

Create a `.env` file with real Trading212 credentials (demo account), then run:

```bash
pip install -r requirements.txt

python -c "
from bot.config import Config
from bot.broker import Trading212Broker
from bot.state import load_state, save_state, reset_daily_state

# Test config
c = Config.from_env()
print(f'Environment: {c.t212_environment}')
print(f'Watchlist: {list(c.watchlist.keys())}')

# Test broker auth
b = Trading212Broker(c.t212_api_key, c.t212_api_secret, c.t212_environment)
positions = b.get_open_positions()
print(f'Open positions: {positions}')

# Test state
s = load_state()
s = reset_daily_state(s)
save_state(s)
s2 = load_state()
print(f'State round-trip OK: {s == s2}')

print('Phase 1 PASSED')
"
```

Expected: No errors, prints environment, watchlist, positions (likely empty list), and "Phase 1 PASSED".

If `get_open_positions()` returns an empty list but no error, that's fine — it means the API key doesn't have portfolio permissions. The auth itself worked (no 401).
