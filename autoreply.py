"""Автоответчик: на новый НЕотвеченный диалог отправляет приветствие + перевод на WhatsApp.
Безопасность: отвечает один раз на тред, только если есть сообщение клиента и ещё нет нашего ответа.
Флаги: AUTOREPLY_ENABLED (планировщик), AUTOREPLY_DRYRUN (не слать, только считать),
AUTOREPLY_LIMIT (макс за прогон), AUTOREPLY_SINCE (ISO-дата: отвечать только на чаты новее неё),
AUTOREPLY_FORCE_SEND=1 (аварийный форс реальной отправки)."""
import os
from client import OlxClient
import storage
from auth import _load

import datetime as _dt
LAST = {"status": "ещё не запускался"}

DEFAULT_TEXT = ("Здравствуйте! 🙌 Спасибо за обращение. Напишите нам, пожалуйста, в WhatsApp: "
                "{wa} ({wame}) — там ответим сразу и рассчитаем стоимость.")

def load_whatsapp_config():
    import json
    config_file = "config_whatsapp.json"
    default_config = {
        "enabled": os.getenv("AUTOREPLY_ENABLED", "0"),
        "interval": os.getenv("AUTOREPLY_EVERY_MIN", "15"),
        "wa_number": os.getenv("AUTOREPLY_WA", ""),
        "text_template": DEFAULT_TEXT,
        "since_date": os.getenv("AUTOREPLY_SINCE", "")
    }
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in default_config.items():
                    data.setdefault(k, v)
                return data
        except:
            pass
    return default_config

def _wa(account):
    config_data = load_whatsapp_config()
    g = config_data.get("wa_number", "")
    g = "".join(ch for ch in str(g) if ch.isdigit())
    if not g:
        g = "".join(ch for ch in str(account) if ch.isdigit())
    return ("+"+g if g else str(account)), ("wa.me/"+g if g else "")

def _epoch(v):
    """created_at -> unix-секунды; понимает ISO ('2026-06-26T13:00:00+05:00'/'...Z') и число.
    Наивное время трактуем как Asia/Almaty (+05)."""
    if v is None or str(v).strip() == "":
        return None
    try:
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).strip()
        if s.isdigit():
            return float(s)
        s = s.replace("Z", "+00:00")
        d = _dt.datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=_dt.timezone(_dt.timedelta(hours=5)))
        return d.timestamp()
    except Exception:
        return None

def run_autoreply(dry=None, limit=None):
    config_data = load_whatsapp_config()
    if dry is None:
        dry = (config_data.get("enabled") != "1")
    if os.getenv("AUTOREPLY_FORCE_SEND") == "1":
        dry = False  # аварийный форс реальной отправки независимо от web.py
    limit = int(os.getenv("AUTOREPLY_LIMIT", "30")) if limit is None else limit
    tmpl = config_data.get("text_template", DEFAULT_TEXT)
    since = _epoch(config_data.get("since_date"))   # отвечаем только на чаты новее этой даты
    global LAST
    SCAN = int(os.getenv("AUTOREPLY_SCAN", "80"))
    scanned = 0
    out = {"sent": 0, "would": 0, "dry": dry, "limit": limit,
           "since": os.getenv("AUTOREPLY_SINCE") or None, "skipped_old": 0, "accounts": {}}
    LAST = {"status": "идёт прогон...", "dry": dry, "scanned": 0, "would": 0, "sent": 0}
    for acc in list(_load().keys()):
        cl = OlxClient(acc); wa, wame = _wa(acc); text = tmpl.format(wa=wa, wame=wame)
        try:
            th = cl.threads(); td = th.get("data", th) if isinstance(th, dict) else th
        except Exception as e:
            out["accounts"][acc] = {"error": str(e)}; continue
        rep = 0
        for t in (td or []):
            if out["sent"] >= limit or scanned >= SCAN: break
            tid = t.get("id")
            if not tid or storage.is_replied(acc, tid): continue
            if (t.get("unread_count") or 0) <= 0: continue   # клиент ничего нового не писал
            if scanned >= SCAN: break
            scanned += 1
            if scanned % 5 == 0:
                LAST = {"status": f"идёт... проверено {scanned}", "scanned": scanned,
                        "would": out["would"], "sent": out["sent"], "dry": dry}
            try:
                ms = cl.thread_messages(tid); m = ms.get("data", ms) if isinstance(ms, dict) else ms
            except Exception:
                continue
            m = m or []
            recvd = [x for x in m if x.get("type") == "received"]
            if recvd and not any(x.get("type") == "sent" for x in m):
                if since is not None:
                    last_recv = max((_epoch(x.get("created_at")) or 0) for x in recvd)
                    if last_recv <= since:
                        out["skipped_old"] += 1   # старый чат до момента включения — не трогаем
                        continue
                if dry:
                    out["would"] += 1
                else:
                    try:
                        cl.post_message(tid, text); storage.mark_replied(acc, tid); out["sent"] += 1; rep += 1
                    except Exception as e:
                        out["accounts"][acc] = {"post_error": str(e), "replied_before_error": rep}
                        out["fatal_post_error"] = str(e)
                        out["status"] = "ошибка отправки"; out["scanned"] = scanned
                        out["finished_at"] = _dt.datetime.now().isoformat()
                        LAST = out
                        print(f"[autoreply] POST error: {e}", flush=True)
                        return out
        out["accounts"][acc] = {"replied": rep}
        LAST = {"status": f"идёт... кабинет {acc} готов", "scanned": scanned,
                "would": out["would"], "sent": out["sent"], "dry": dry, "accounts": dict(out["accounts"])}
        if scanned >= SCAN: break
    out["scanned"] = scanned
    out["status"] = "готово"; out["finished_at"] = _dt.datetime.now().isoformat()
    LAST = out
    print(f"[autoreply] dry={dry} sent={out['sent']} would={out['would']}", flush=True)
    return out
