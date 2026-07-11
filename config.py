"""Конфигурация. Значения берутся из .env (см. .env.example)."""
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# --- Эндпоинты OLX (из официальной OpenAPI-спеки v2) ---
API_BASE      = "https://www.olx.kz/api/partner"
TOKEN_URL     = "https://www.olx.kz/api/open/oauth/token"
AUTHORIZE_URL = "https://www.olx.kz/oauth/authorize"
API_VERSION   = "2.0"   # обязательный заголовок Version

# --- Креды приложения ---
CLIENT_ID     = os.getenv("OLX_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("OLX_CLIENT_SECRET", "")
REDIRECT_URI  = os.getenv("OLX_REDIRECT_URI", "http://localhost:8000/callback")
SCOPES        = os.getenv("OLX_SCOPES", "v2 read write")

# --- Локальное хранилище ---
DATA_DIR = os.getenv("DATA_DIR", ".")           # на Railway смонтируй volume сюда (напр. /data)
DB_PATH  = os.getenv("DB_PATH", os.path.join(DATA_DIR, "olx.db"))

# --- Предохранители / пороги ---
PROMO_DAILY_BUDGET_KZT = float(os.getenv("PROMO_DAILY_BUDGET_KZT", "5000"))
PROMO_MIN_HOURS_BETWEEN = int(os.getenv("PROMO_MIN_HOURS_BETWEEN", "20"))
LOW_VIEWS_THRESHOLD = int(os.getenv("LOW_VIEWS_THRESHOLD", "15"))
ZERO_LEADS_DAYS = int(os.getenv("ZERO_LEADS_DAYS", "4"))
