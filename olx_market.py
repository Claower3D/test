"""Мониторинг продвижения ЧУЖИХ объявлений на OLX по их ID.

OLX отдаёт публично по любому активному объявлению (без токенов):
  GET https://www.olx.kz/api/v1/offers/{id}/
Оттуда видно ПРИЗНАКИ ПРОДВИЖЕНИЯ конкурента:
  - top_ad / highlighted / urgent / premium / b2c (платные опции),
  - дату создания и дату последнего поднятия (last_refresh_time),
  - цену, город, заголовок, имя продавца.

Просмотры/звонки по чужим объявлениям OLX НЕ отдаёт (это приватные данные) —
поэтому меряем именно продвижение: что включено и как часто поднимают.
"""
import datetime

try:
    import requests
except Exception:
    requests = None

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
_HEADERS = {"User-Agent": _UA,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ru,kk;q=0.8,en;q=0.5",
            "Referer": "https://www.olx.kz/"}

_API = "https://www.olx.kz/api/v1/offers/%s/"


def _date(s):
    """ISO-время OLX -> 'дд.мм' и datetime (для расчёта давности)."""
    if not s:
        return "", None
    try:
        dt = datetime.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y"), dt
    except Exception:
        return str(s)[:10], None


def _price(params):
    for p in params or []:
        if p.get("key") == "price":
            v = p.get("value") or {}
            return v.get("label") or (str(v.get("value")) if v.get("value") is not None else "")
    return ""


def fetch_offer(offer_id, timeout=10):
    """Вернёт dict по одному чужому объявлению.
    {ok, id, title, url, seller, city, price, top, highlighted, urgent, premium,
     created, refreshed, refreshed_dt, days_since_refresh, options, error}
    """
    r = {"ok": False, "id": str(offer_id), "title": "", "url": "", "seller": "",
         "city": "", "price": "", "top": False, "highlighted": False, "urgent": False,
         "premium": False, "created": "", "refreshed": "", "refreshed_dt": None,
         "days_since_refresh": None, "options": [], "error": None}
    if requests is None:
        r["error"] = "requests недоступен"
        return r
    try:
        resp = requests.get(_API % offer_id, headers=_HEADERS, timeout=timeout)
    except Exception as e:
        r["error"] = "сеть: %s" % e
        return r
    if resp.status_code == 404:
        r["error"] = "не найдено (неактивно/удалено/на модерации)"
        return r
    if resp.status_code != 200:
        r["error"] = "HTTP %s" % resp.status_code
        return r
    try:
        d = (resp.json() or {}).get("data") or {}
    except Exception:
        r["error"] = "не JSON"
        return r
    if not d:
        r["error"] = "пустой ответ"
        return r

    promo = d.get("promotion") or {}
    opts = promo.get("options") or []
    r["title"] = d.get("title") or ""
    r["url"] = d.get("url") or (_API % offer_id)
    user = d.get("user") or {}
    r["seller"] = user.get("name") or ""
    loc = d.get("location") or {}
    city = loc.get("city") or {}
    r["city"] = (city.get("name") if isinstance(city, dict) else city) or ""
    r["price"] = _price(d.get("params"))
    r["top"] = bool(promo.get("top_ad"))
    r["highlighted"] = bool(promo.get("highlighted"))
    r["urgent"] = bool(promo.get("urgent"))
    r["premium"] = bool(promo.get("premium_ad_page") or promo.get("b2c_ad_page"))
    r["options"] = opts
    r["created"], _ = _date(d.get("created_time"))
    r["refreshed"], rdt = _date(d.get("last_refresh_time"))
    r["refreshed_dt"] = rdt
    if rdt is not None:
        now = datetime.datetime.now(rdt.tzinfo) if rdt.tzinfo else datetime.datetime.now()
        r["days_since_refresh"] = (now - rdt).days
    r["ok"] = True
    return r


def fetch_many(ids, timeout=10):
    return [fetch_offer(i, timeout=timeout) for i in ids]


if __name__ == "__main__":
    import json
    print(json.dumps(fetch_many([397610224, 397610305, 397610369]),
                     ensure_ascii=False, indent=2, default=str))
