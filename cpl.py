"""CPL по аккаунту/нише.
ВАЖНО: phone_views — прокси звонков (показ телефона), threads — лиды из чата.
Истинный CPA по продажам считается связкой с CRM (см. README)."""
import datetime
import storage

def cpl_report(account="default", day=None):
    day = day or datetime.date.today().isoformat()
    c = storage.conn()
    spend = c.execute("SELECT COALESCE(spend_kzt,0) s FROM billing WHERE account=? AND day=?",
                      (account, day)).fetchone()
    spend = spend["s"] if spend else 0.0
    rows = c.execute("""SELECT SUM(phone_views) pv, SUM(threads) th
        FROM stats s JOIN adverts a ON a.id=s.advert_id
        WHERE a.account=? AND s.day=?""", (account, day)).fetchone()
    c.close()
    phone = rows["pv"] or 0
    chat = rows["th"] or 0
    leads = phone + chat
    cpl = (spend / leads) if leads else None
    return {
        "account": account, "day": day, "spend_kzt": spend,
        "phone_reveals": phone, "chat_leads": chat, "leads_total": leads,
        "cpl_kzt": round(cpl, 1) if cpl is not None else None,
        "note": "CPL по контактам (звонки+чат). Для CPA по продажам нужна CRM-атрибуция.",
    }
