"""Движок правил: оптимизация неэффективных, автоподнятие (с бюджетом), lifecycle.
По умолчанию работает в DRY-RUN: ничего не меняет, только предлагает. Передай apply=True для боя."""
import datetime
import config
from client import OlxClient
import storage

def _today_stats(account):
    day = datetime.date.today().isoformat()
    c = storage.conn()
    rows = c.execute("""SELECT a.id, a.title, a.status, s.advert_views, s.phone_views, s.threads
        FROM adverts a JOIN stats s ON s.advert_id=a.id
        WHERE a.account=? AND s.day=?""", (account, day)).fetchall()
    c.close(); return rows

# --- 1. Кандидаты на оптимизацию ---
def optimization_candidates(account="default"):
    out = []
    for r in _today_stats(account):
        leads = (r["phone_views"] or 0) + (r["threads"] or 0)
        if (r["advert_views"] or 0) < config.LOW_VIEWS_THRESHOLD or leads == 0:
            out.append({"id": r["id"], "title": r["title"],
                        "views": r["advert_views"], "leads": leads,
                        "reason": "мало просмотров/0 обращений"})
    return out

# --- 2. Автоподнятие с бюджет-предохранителем ---
def promote(account="default", apply=False):
    """Поднимает топ-перформеров, пока не исчерпан дневной бюджет."""
    client = OlxClient(account)
    budget = config.PROMO_DAILY_BUDGET_KZT
    spent = storage.promo_spent_today(account)
    rows = sorted(_today_stats(account),
                  key=lambda r: (r["phone_views"] or 0), reverse=True)
    actions = []
    try:
        features = client.paid_features() or []
        bump = _pick_bump_feature(features)
    except Exception as e:
        return {"error": f"paid-features недоступны: {e}"}

    for r in rows:
        if not bump:
            break
        cost = float(bump.get("price_kzt", bump.get("price", 0)) or 0)
        if spent + cost > budget:
            break  # бюджет-предохранитель
        actions.append({"id": r["id"], "code": bump.get("code"), "cost": cost})
        if apply:
            client.purchase_paid_feature(r["id"], bump.get("code"))
            storage.log_promo(r["id"], bump.get("code"), cost, account)
        spent += cost
    return {"apply": apply, "budget": budget, "spent_after": spent, "actions": actions}

def _pick_bump_feature(features):
    """Выбрать опцию поднятия (тип topads/bump). Структура зависит от рынка."""
    data = features.get("data", features) if isinstance(features, dict) else features
    for f in (data or []):
        if str(f.get("type", "")).lower() in ("topads", "bump", "promote"):
            return f
    return (data or [None])[0]

# --- 3. Lifecycle: deactivate -> delete по жёстким правилам ---
def lifecycle_delete(advert_id, account="default", apply=False):
    """Двухшаговое удаление: сначала deactivate, потом delete (требование API)."""
    client = OlxClient(account)
    plan = ["deactivate", "delete"]
    if apply:
        client.command(advert_id, "deactivate")
        client._req("DELETE", f"/adverts/{advert_id}")
    return {"advert_id": advert_id, "apply": apply, "plan": plan}
