import os
"""Дневной сбор: объявления -> статистика + чаты + расход -> SQLite."""
import datetime
from collections import Counter
from client import OlxClient
import storage

def _thread_counts_by_advert(client):
    """Сколько чат-тредов на каждое объявление (лиды из переписки)."""
    counts = Counter()
    try:
        threads = client.threads()
        data = threads.get("data", threads) if isinstance(threads, dict) else threads
        for t in (data or []):
            aid = t.get("advert_id") or (t.get("advert") or {}).get("id")
            if aid:
                counts[aid] += 1
    except Exception as e:
        print("  ! чаты недоступны:", e)
    return counts

def collect(account="default"):
    storage.init()
    client = OlxClient(account)
    adverts = client.all_adverts()
    print(f"[{account}] объявлений: {len(adverts)}")
    thread_counts = _thread_counts_by_advert(client)

    for a in adverts:
        aid = a.get("id")
        storage.upsert_advert(a, account)
        try:
            st = client.statistics(aid) or {}
        except Exception as e:
            print(f"  ! статистика {aid}: {e}"); st = {}
        storage.save_stats(aid, st, thread_counts.get(aid, 0))
        if os.getenv("PF_ENABLED"):   # чтение платных услуг закрыто 403 — включить после выдачи доступа OLX
            try:
                pf = client.active_paid_features(aid) or []
                pf = pf.get("data", pf) if isinstance(pf, dict) else pf
                vts = [f.get("valid_to") for f in (pf or []) if f.get("valid_to")]
                storage.update_promo(aid, max(vts) if vts else None,
                                     (pf[0].get("type") if pf else None))
            except Exception:
                pass

    # расход и баланс
    try:
        bal = client.account_balance() or {}
        storage.save_billing(account, spend=0.0, balance=bal.get("sum", 0))
    except Exception as e:
        print("  ! баланс недоступен:", e)
    print(f"[{account}] собрано {datetime.date.today()}")
    return adverts
