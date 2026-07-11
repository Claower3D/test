"""Тонкая обёртка над OLX Partner API. Все методы возвращают распарсенный JSON."""
import time, requests
import config
from auth import get_valid_token


class OlxClient:
    def __init__(self, account: str = "default"):
        self.account = account
        self.s = requests.Session()

    def _headers(self):
        return {
            "Authorization": f"Bearer {get_valid_token(self.account)}",
            "Version": config.API_VERSION,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _req(self, method: str, path: str, **kw):
        url = config.API_BASE + path
        for attempt in range(5):
            r = self.s.request(method, url, headers=self._headers(), timeout=30, **kw)
            if r.status_code == 429:            # рейт-лимит -> экспоненциальная пауза
                time.sleep(2 ** attempt)
                continue
            r.raise_for_status()
            return r.json() if r.text else None
        raise RuntimeError(f"429 throttled: {method} {path}")

    # --- Пользователь / деньги ---
    def me(self):                      return self._req("GET", "/users/me")
    def account_balance(self):         return self._req("GET", "/users/me/account-balance")
    def billing(self):                 return self._req("GET", "/users/me/billing")

    # --- Объявления ---
    def adverts(self, offset=0, limit=100):
        return self._req("GET", f"/adverts?offset={offset}&limit={limit}")

    def all_adverts(self):
        out, off = [], 0
        while True:
            page = self._req("GET", f"/adverts?offset={off}&limit=50")
            data = page.get("data", page) if isinstance(page, dict) else page
            if not data:
                break
            out.extend(data)
            if len(data) < 50:
                break
            off += 50
        return out

    def advert(self, advert_id):       return self._req("GET", f"/adverts/{advert_id}")
    def update_advert(self, advert_id, payload):
        return self._req("PUT", f"/adverts/{advert_id}", json=payload)
    def command(self, advert_id, command, **extra):
        body = {"command": command, **extra}
        return self._req("POST", f"/adverts/{advert_id}/commands", json=body)
    def statistics(self, advert_id):
        r = self._req("GET", f"/adverts/{advert_id}/statistics")
        return (r.get("data", r) if isinstance(r, dict) else r) or {}

    # --- Платное продвижение ---
    def paid_features(self):           return self._req("GET", "/paid-features")
    def active_paid_features(self, advert_id):
        return self._req("GET", f"/adverts/{advert_id}/paid-features")
    def purchase_paid_feature(self, advert_id, code):
        return self._req("POST", f"/adverts/{advert_id}/paid-features", json={"code": code})

    # --- Чат (лиды) ---
    def threads(self):                 return self._req("GET", "/threads")
    def thread_messages(self, thread_id):
        return self._req("GET", f"/threads/{thread_id}/messages")
    def post_message(self, thread_id, text):
        return self._req("POST", f"/threads/{thread_id}/messages", json={"text": text})
