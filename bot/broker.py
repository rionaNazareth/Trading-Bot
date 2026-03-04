import base64
import logging
import time

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
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                response = httpx.request(
                    method, f"{self.base_url}{path}", headers=self.headers, **kwargs
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP {e.response.status_code} on {method} {path}: {e.response.text}"
                )
                return None
            except httpx.RequestError as e:
                logger.error(
                    f"Network error on {method} {path} (attempt {attempt}/{max_attempts}): {e}"
                )
                if attempt == max_attempts:
                    return None
                time.sleep(1)
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
            "POST",
            "/equity/orders/market",
            json={"ticker": ticker, "quantity": quantity},
        )

    def close_position(self, ticker: str, quantity: int) -> dict | None:
        return self._request(
            "POST",
            "/equity/orders/market",
            json={"ticker": ticker, "quantity": -quantity},
        )

    def place_limit_order(
        self,
        ticker: str,
        quantity: int,
        limit_price: float,
        stop_price: float | None = None,
        take_profit: float | None = None,
    ) -> dict | None:
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

    def place_stop_order(
        self,
        ticker: str,
        quantity: int,
        stop_price: float,
    ) -> dict | None:
        return self._request(
            "POST",
            "/equity/orders/stop",
            json={"ticker": ticker, "quantity": quantity, "stopPrice": stop_price},
        )

