"""OAuth2 для OLX Partner API: authorization_code + refresh_token, с хранением токенов.
Поддерживает несколько аккаунтов (token store по метке аккаунта)."""
import json, os, time, urllib.parse, requests
import config

TOKENS_FILE = os.getenv("OLX_TOKENS_FILE", os.path.join(config.DATA_DIR, "tokens.json"))


def _load() -> dict:
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save(data: dict):
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_authorize_url(state: str = "olx") -> str:
    """Ссылка, по которой ВЛАДЕЛЕЦ аккаунта подтверждает доступ (OAuth — действие пользователя)."""
    q = urllib.parse.urlencode({
        "client_id": config.CLIENT_ID,
        "redirect_uri": config.REDIRECT_URI,
        "response_type": "code",
        "scope": config.SCOPES,
        "state": state,
    })
    return f"{config.AUTHORIZE_URL}?{q}"


def exchange_code(code: str, account: str = "default") -> dict:
    """Обмен authorization_code на токены (вызывается один раз после авторизации)."""
    r = requests.post(config.TOKEN_URL, data={
        "grant_type": "authorization_code",
        "client_id": config.CLIENT_ID,
        "client_secret": config.CLIENT_SECRET,
        "redirect_uri": config.REDIRECT_URI,
        "scope": config.SCOPES,
        "code": code,
    }, timeout=30)
    r.raise_for_status()
    tok = r.json()
    _store(account, tok)
    return tok


def _store(account: str, tok: dict):
    data = _load()
    tok["_expires_at"] = time.time() + int(tok.get("expires_in", 3600)) - 60
    data[account] = tok
    _save(data)


def _refresh(account: str, tok: dict) -> dict:
    r = requests.post(config.TOKEN_URL, data={
        "grant_type": "refresh_token",
        "client_id": config.CLIENT_ID,
        "client_secret": config.CLIENT_SECRET,
        "refresh_token": tok["refresh_token"],
        "scope": config.SCOPES,
    }, timeout=30)
    r.raise_for_status()
    new = r.json()
    # OLX может не вернуть новый refresh_token — сохраняем старый
    new.setdefault("refresh_token", tok["refresh_token"])
    _store(account, new)
    return new


def get_valid_token(account: str = "default") -> str:
    """Вернуть валидный access_token, обновив по refresh при необходимости."""
    data = _load()
    if account not in data:
        raise RuntimeError(
            f"Нет токена для '{account}'. Запусти: python run.py auth")
    tok = data[account]
    if time.time() >= tok.get("_expires_at", 0):
        tok = _refresh(account, tok)
    return tok["access_token"]
