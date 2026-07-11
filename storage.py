"""SQLite-хранилище истории: объявления, дневные снимки статистики, чаты, расход."""
import sqlite3, datetime, config

def conn():
    c = sqlite3.connect(config.DB_PATH, timeout=15, check_same_thread=False)
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA synchronous=NORMAL;")
    c.row_factory = sqlite3.Row
    return c

def init():
    c = conn(); q = c.execute
    q("""CREATE TABLE IF NOT EXISTS adverts(
        id INTEGER PRIMARY KEY, account TEXT, external_id TEXT, title TEXT,
        category_id INTEGER, status TEXT, city TEXT, created_at TEXT, last_seen TEXT)""")
    q("""CREATE TABLE IF NOT EXISTS stats(
        advert_id INTEGER, day TEXT, advert_views INTEGER, phone_views INTEGER,
        users_observing INTEGER, threads INTEGER,
        PRIMARY KEY(advert_id, day))""")
    q("""CREATE TABLE IF NOT EXISTS billing(
        account TEXT, day TEXT, spend_kzt REAL, balance_kzt REAL,
        PRIMARY KEY(account, day))""")
    q("""CREATE TABLE IF NOT EXISTS categories(
        id INTEGER PRIMARY KEY, name TEXT)""")
    q("""CREATE TABLE IF NOT EXISTS cities(
        id INTEGER PRIMARY KEY, name TEXT)""")
    q("""CREATE TABLE IF NOT EXISTS promo_log(
        advert_id INTEGER, ts TEXT, code TEXT, est_cost_kzt REAL, account TEXT)""")
    q("""CREATE TABLE IF NOT EXISTS pos_cache(
        ckey TEXT PRIMARY KEY, ts REAL, data_json TEXT)""")
    for col in ("activated_at","valid_to","top_until","promo_type","url"):
        try: q("ALTER TABLE adverts ADD COLUMN "+col+" TEXT")
        except Exception: pass
    try: q("ALTER TABLE categories ADD COLUMN kind TEXT")
    except Exception: pass
    try: q("ALTER TABLE categories ADD COLUMN rubric TEXT")
    except Exception: pass
    q("""CREATE TABLE IF NOT EXISTS replied_threads(account TEXT, thread_id INTEGER, ts TEXT, PRIMARY KEY(account, thread_id))""")
    c.commit(); c.close()

def _city_of(a):
    loc = a.get("location") or {}
    if isinstance(loc, dict):
        if loc.get("city_id") is not None:
            return loc.get("city_id")
        cc = loc.get("city")
        if isinstance(cc, dict): return cc.get("name")
        if isinstance(cc, str):  return cc
        if loc.get("city_name"): return loc.get("city_name")
    return a.get("city")

def upsert_advert(a, account):
    c = conn()
    c.execute("""INSERT INTO adverts(id,account,external_id,title,category_id,status,city,created_at,last_seen)
        VALUES(?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET status=excluded.status, last_seen=excluded.last_seen,
        title=excluded.title, city=excluded.city, category_id=excluded.category_id""",
        (a.get("id"), account, a.get("external_id"), a.get("title"), a.get("category_id"),
         a.get("status"), _city_of(a), a.get("created_at"),
         datetime.date.today().isoformat()))
    c.execute("UPDATE adverts SET activated_at=?, valid_to=? WHERE id=?",
              (a.get("activated_at"), a.get("valid_to"), a.get("id")))
    c.execute("UPDATE adverts SET url=? WHERE id=?", (a.get("url"), a.get("id")))
    c.commit(); c.close()

def save_stats(advert_id, st, threads_count, day=None):
    day = day or datetime.date.today().isoformat()
    c = conn()
    c.execute("""INSERT INTO stats(advert_id,day,advert_views,phone_views,users_observing,threads)
        VALUES(?,?,?,?,?,?)
        ON CONFLICT(advert_id,day) DO UPDATE SET advert_views=excluded.advert_views,
        phone_views=excluded.phone_views, users_observing=excluded.users_observing,
        threads=excluded.threads""",
        (advert_id, day, st.get("advert_views",0), st.get("phone_views",0),
         st.get("users_observing",0), threads_count))
    c.commit(); c.close()

def save_billing(account, spend, balance, day=None):
    day = day or datetime.date.today().isoformat()
    c = conn()
    c.execute("""INSERT INTO billing(account,day,spend_kzt,balance_kzt) VALUES(?,?,?,?)
        ON CONFLICT(account,day) DO UPDATE SET spend_kzt=excluded.spend_kzt,
        balance_kzt=excluded.balance_kzt""", (account, day, spend, balance))
    c.commit(); c.close()

def promo_spent_today(account, day=None):
    day = day or datetime.date.today().isoformat()
    c = conn()
    row = c.execute("SELECT COALESCE(SUM(est_cost_kzt),0) s FROM promo_log "
                    "WHERE account=? AND substr(ts,1,10)=?", (account, day)).fetchone()
    c.close(); return row["s"]

def log_promo(advert_id, code, cost, account):
    c = conn()
    c.execute("INSERT INTO promo_log(advert_id,ts,code,est_cost_kzt,account) VALUES(?,?,?,?,?)",
              (advert_id, datetime.datetime.now().isoformat(), code, cost, account))
    c.commit(); c.close()


def category_names():
    c=conn(); rows=c.execute("SELECT id,name FROM categories").fetchall(); c.close()
    return {r["id"]:r["name"] for r in rows}

def save_category(cid,name,kind=None,rubric=None):
    c=conn()
    c.execute("INSERT INTO categories(id,name,kind,rubric) VALUES(?,?,?,?) "
              "ON CONFLICT(id) DO UPDATE SET name=excluded.name, "
              "kind=COALESCE(excluded.kind, categories.kind), "
              "rubric=COALESCE(excluded.rubric, categories.rubric)",(cid,name,kind,rubric))
    c.commit(); c.close()

def category_kinds():
    c=conn(); rows=c.execute("SELECT id,kind FROM categories").fetchall(); c.close()
    return {r["id"]:r["kind"] for r in rows}

def category_rubrics():
    c=conn(); rows=c.execute("SELECT id,rubric FROM categories").fetchall(); c.close()
    return {r["id"]:r["rubric"] for r in rows}

def latest_rows():
    c=conn()
    rows=c.execute("""SELECT a.id,a.account,a.title,a.category_id,a.city,a.status,a.url,
        s.advert_views,s.phone_views,s.threads,s.day,
        p.advert_views AS prev_views, p.phone_views AS prev_phone
        FROM adverts a
        JOIN stats s ON s.advert_id=a.id
          AND s.day=(SELECT MAX(day) FROM stats WHERE advert_id=a.id)
        LEFT JOIN stats p ON p.advert_id=a.id
          AND p.day=(SELECT MAX(day) FROM stats WHERE advert_id=a.id AND day < s.day)
        WHERE a.status='active'
        ORDER BY s.phone_views DESC""").fetchall()
    c.close(); return [dict(r) for r in rows]

def advert_history(advert_id):
    c=conn()
    rows=c.execute("SELECT day,advert_views,phone_views,threads FROM stats WHERE advert_id=? ORDER BY day",(advert_id,)).fetchall()
    c.close(); return [dict(r) for r in rows]

def advert_meta(advert_id):
    c=conn()
    r=c.execute("SELECT id,account,title,category_id,city FROM adverts WHERE id=?",(advert_id,)).fetchone()
    c.close(); return dict(r) if r else None


def city_names():
    c=conn(); rows=c.execute("SELECT id,name FROM cities").fetchall(); c.close()
    return {r["id"]:r["name"] for r in rows}

def save_city(cid,name):
    c=conn()
    c.execute("INSERT INTO cities(id,name) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name",(cid,name))
    c.commit(); c.close()


def update_promo(advert_id, top_until, promo_type):
    c=conn()
    c.execute("UPDATE adverts SET top_until=?, promo_type=? WHERE id=?",(top_until,promo_type,advert_id))
    c.commit(); c.close()

def set_advert_status(advert_id, status):
    c=conn()
    c.execute("UPDATE adverts SET status=? WHERE id=?",(status,advert_id))
    c.commit(); c.close()

def weekly_rows(start_day, end_day):
    c=conn()
    rows=c.execute("""
      SELECT a.id,a.account,a.title,a.category_id,a.city,a.created_at,a.activated_at,a.valid_to,a.top_until,a.promo_type,a.url,
        (SELECT advert_views FROM stats WHERE advert_id=a.id AND day BETWEEN ? AND ? ORDER BY day ASC  LIMIT 1) AS s_v,
        (SELECT phone_views  FROM stats WHERE advert_id=a.id AND day BETWEEN ? AND ? ORDER BY day ASC  LIMIT 1) AS s_p,
        (SELECT threads      FROM stats WHERE advert_id=a.id AND day BETWEEN ? AND ? ORDER BY day ASC  LIMIT 1) AS s_t,
        (SELECT advert_views FROM stats WHERE advert_id=a.id AND day BETWEEN ? AND ? ORDER BY day DESC LIMIT 1) AS e_v,
        (SELECT phone_views  FROM stats WHERE advert_id=a.id AND day BETWEEN ? AND ? ORDER BY day DESC LIMIT 1) AS e_p,
        (SELECT threads      FROM stats WHERE advert_id=a.id AND day BETWEEN ? AND ? ORDER BY day DESC LIMIT 1) AS e_t
      FROM adverts a WHERE a.status='active'
      ORDER BY e_p DESC
    """, (start_day,end_day)*6).fetchall()
    c.close(); return [dict(r) for r in rows]


def rename_account(old, new):
    c=conn()
    c.execute("UPDATE adverts SET account=? WHERE account=?", (new, old))
    try: c.execute("UPDATE billing SET account=? WHERE account=?", (new, old))
    except Exception: pass
    c.commit(); c.close()


def is_replied(account, tid):
    c=conn(); r=c.execute("SELECT 1 FROM replied_threads WHERE account=? AND thread_id=?",(account,tid)).fetchone(); c.close(); return bool(r)

def mark_replied(account, tid):
    import datetime as _dt
    c=conn(); c.execute("INSERT OR IGNORE INTO replied_threads(account,thread_id,ts) VALUES(?,?,?)",(account,tid,_dt.datetime.now().isoformat())); c.commit(); c.close()
