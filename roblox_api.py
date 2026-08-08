import time
import random

try:
    import httpx
except ImportError as _exc:
    import sys
    sys.exit(f"missing dependency '{_exc.name}'. run: pip install -r requirements.txt")

BASE = "https://economy.roblox.com"
USER_BASE = "https://users.roblox.com"

class RobloxAPIError(Exception):
    pass

def _jitter() -> float:
    return random.uniform(0.5, 1.5)

def _req(client: httpx.Client, method: str, url: str, **kwargs) -> dict:
    retries = 3
    for attempt in range(retries):
        try:
            r = client.request(method, url, **kwargs)
        except httpx.RequestError as exc:
            raise RobloxAPIError(f"network error: {exc}")

        if r.status_code == 429:
            retry_after = r.headers.get("Retry-After")
            if retry_after:
                wait = float(retry_after) * _jitter()
            else:
                wait = (2 ** attempt) * _jitter()
            time.sleep(wait)
            continue

        if r.status_code >= 500:
            time.sleep(1.0 * _jitter())
            continue

        r.raise_for_status()
        return r.json()

    raise RobloxAPIError("max retries exceeded")

class RobloxClient:
    def __init__(self, cookie: str) -> None:
        self.cookie = cookie
        self._client = httpx.Client(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Cookie": f".ROBLOSECURITY={cookie}",
            },
            timeout=30.0,
        )

    def _get(self, url: str) -> dict:
        return _req(self._client, "GET", url)

    def get_authenticated_user(self) -> dict:
        return self._get(f"{USER_BASE}/v1/users/authenticated")

    def get_currency(self) -> int:
        data = self._get(f"{BASE}/v1/user/currency")
        return data.get("robux", 0)

    def get_transactions(self, limit: int = 50) -> list[dict]:
        results: list[dict] = []
        url = f"{BASE}/v1/transactions?limit={limit}"
        while url and len(results) < limit:
            data = self._get(url)
            batch = data.get("data", [])
            if not batch:
                break
            results.extend(batch)
            next_page = data.get("nextPageCursor")
            if not next_page:
                break
            url = f"{BASE}/v1/transactions?limit={limit}&cursor={next_page}"
        return results[:limit]
