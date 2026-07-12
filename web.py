"""Веб-сервис бота для Railway:
 - страница авторизации аккаунтов OLX (жмёшь 'разрешить' по каждому);
 - приём OAuth-кода и сохранение токена;
 - внутренний планировщик дневного прогона;
 - ручной запуск и простой статус.
Запуск на Railway:  gunicorn web:app   (см. Procfile)
"""
import os, threading
from flask import Flask, send_file, request, redirect, jsonify
import config, storage_init  # noqa
import auth, runner, storage
import datetime as _dt
from client import OlxClient
import json

try:
    import requests as _requests
except Exception:
    _requests = None

scheduler = None

def load_whatsapp_config():
    config_file = "config_whatsapp.json"
    default_config = {
        "enabled": os.getenv("AUTOREPLY_ENABLED", "0"),
        "interval": os.getenv("AUTOREPLY_EVERY_MIN", "15"),
        "wa_number": os.getenv("AUTOREPLY_WA", ""),
        "text_template": "Здравствуйте! 🙌 Спасибо за обращение. Напишите нам, пожалуйста, в WhatsApp: {wa} ({wame}) — там ответим сразу и рассчитаем стоимость.",
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

def save_whatsapp_config(data):
    config_file = "config_whatsapp.json"
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False


def load_whatsapp_groups():
    import json
    config_file = "whatsapp_groups.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return []

def save_whatsapp_groups(data):
    import json
    config_file = "whatsapp_groups.json"
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

def update_scheduler_jobs():
    global scheduler
    if not scheduler:
        return
    try:
        scheduler.remove_job("autoreply_job")
    except:
        pass
        
    config_data = load_whatsapp_config()
    if config_data.get("enabled") == "1":
        try:
            every = int(config_data.get("interval", "15"))
        except:
            every = 15
        import autoreply
        scheduler.add_job(
            autoreply.run_autoreply, 
            "interval", 
            minutes=every, 
            id="autoreply_job",
            kwargs={"dry": False}
        )
        print(f"[scheduler] Автоответчик WhatsApp включён: каждые {every} мин")

# Конкуренты под наблюдением: метка -> список ID объявлений OLX.
COMPETITORS = {
    "OLX ABDU ATA": ["397610224", "397610305", "397610369"],
}
# Ключ поиска по умолчанию для расчёта позиции (по нему считаем место в выдаче).
COMPETITOR_QUERY = {
    "OLX ABDU ATA": "москитные сетки",
}

_PROMO_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru,kk;q=0.8,en;q=0.5",
    "Referer": "https://www.olx.kz/",
}


def _promo_date(s):
    if not s:
        return "", None
    try:
        d = _dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return d.strftime("%d.%m.%Y"), d
    except Exception:
        return str(s)[:10], None


def _promo_price(params):
    for p in params or []:
        if p.get("key") == "price":
            v = p.get("value") or {}
            return v.get("label") or (str(v.get("value")) if v.get("value") is not None else "")
    return ""


def fetch_offer(offer_id, timeout=10):
    """Публичные признаки продвижения чужого объявления по его ID (без токенов).
    OLX: GET /api/v1/offers/{id}/ — отдаёт top_ad/highlighted/urgent/премиум,
    дату создания и последнего поднятия, цену, город, продавца. Просмотры/звонки
    по чужим объявлениям OLX не отдаёт (приватные данные)."""
    r = {"ok": False, "id": str(offer_id), "title": "", "url": "", "seller": "",
         "city": "", "price": "", "top": False, "highlighted": False, "urgent": False,
         "premium": False, "created": "", "refreshed": "", "days_since_refresh": None,
         "category_id": None, "category_name": "", "city_id": None, "region_id": None,
         "error": None}
    if _requests is None:
        r["error"] = "requests недоступен"; return r
    try:
        resp = _requests.get("https://www.olx.kz/api/v1/offers/%s/" % offer_id,
                             headers=_PROMO_HEADERS, timeout=timeout)
    except Exception as e:
        r["error"] = "сеть: %s" % e; return r
    if resp.status_code == 404:
        r["error"] = "не найдено (неактивно/удалено/на модерации)"; return r
    if resp.status_code != 200:
        r["error"] = "HTTP %s" % resp.status_code; return r
    try:
        d = (resp.json() or {}).get("data") or {}
    except Exception:
        r["error"] = "не JSON"; return r
    if not d:
        r["error"] = "пустой ответ"; return r
    promo = d.get("promotion") or {}
    r["title"] = d.get("title") or ""
    r["url"] = d.get("url") or ("https://www.olx.kz/api/v1/offers/%s/" % offer_id)
    r["seller"] = (d.get("user") or {}).get("name") or ""
    loc = d.get("location") or {}; city = loc.get("city") or {}; region = loc.get("region") or {}
    r["city"] = (city.get("name") if isinstance(city, dict) else city) or ""
    if isinstance(city, dict):
        r["city_id"] = city.get("id")
    r["city_id"] = r["city_id"] or loc.get("city_id")
    if isinstance(region, dict):
        r["region_id"] = region.get("id")
    cat = d.get("category") or {}
    r["category_id"] = (cat.get("id") if isinstance(cat, dict) else cat) or d.get("category_id")
    if r["category_id"]:
        r["category_name"] = _olx_cat_name(r["category_id"], r.get("url"))
    r["price"] = _promo_price(d.get("params"))
    r["top"] = bool(promo.get("top_ad"))
    r["highlighted"] = bool(promo.get("highlighted"))
    r["urgent"] = bool(promo.get("urgent"))
    r["premium"] = bool(promo.get("premium_ad_page") or promo.get("b2c_ad_page"))
    r["created"], _ = _promo_date(d.get("created_time"))
    r["refreshed"], rdt = _promo_date(d.get("last_refresh_time"))
    if rdt is not None:
        now = _dt.datetime.now(rdt.tzinfo) if rdt.tzinfo else _dt.datetime.now()
        r["days_since_refresh"] = (now - rdt).days
    r["ok"] = True
    return r

import re as _re, json as _json

def _olx_cat_name(cat_id, seed_url=None):
    """Название КОНЕЧНОЙ категории по её id из HTML OLX с кэшированием в SQLite."""
    try:
        cid = int(cat_id)
    except Exception:
        return ""
    
    cn = storage.category_names()
    if cid in cn:
        return cn[cid]
        
    if _requests is None or not seed_url:
        return ""
    try:
        resp = _requests.get(seed_url, headers=dict(_PROMO_HEADERS, **{"Accept": "text/html"}), timeout=12)
        html = resp.text or ""
    except Exception:
        return ""
    m = _re.search(r'__PRERENDERED_STATE__\s*=\s*"((?:[^"\\]|\\.)*)"', html)
    state = html
    if m:
        try:
            state = _json.loads('"' + m.group(1) + '"')
        except Exception:
            state = html
    def _dec(s):
        s = _re.sub(r'\\u([0-9a-fA-F]{4})', lambda mm: chr(int(mm.group(1), 16)), s)
        return s.replace('\\/', '/').replace('\\"', '"')
        
    for mm in _re.finditer(r'"id":(\d+),"label":"[^"]*","parentId":\d+,"name":"([^"]+)"', state):
        try:
            storage.save_category(int(mm.group(1)), _dec(mm.group(2)))
        except Exception:
            pass
            
    return storage.category_names().get(cid, "")


def fetch_position(offer, query=None, max_pages=13, per=40, timeout=10):
    """Органическое место чужого объявления в выдаче его рубрики (категория+город),
    БЕЗ учёта платных ТОП-слотов.

    Главное: какие карточки реально занимают платные ТОП-слоты, говорит сам OLX —
    в листинге это metadata.promoted (индексы слотов на странице). НЕ флаг top_ad у
    объявления: пакет «ТОП/Премиум» могут купить многие, но видимых слотов ограниченно;
    остальные платники падают в органику. Поэтому ранг считаем, исключая ровно те
    индексы, что OLX пометил как promoted.
    Кэш 15 мин — позиция меняется медленно, частить = риск бана."""
    res = {"found": False, "organic_rank": None, "page": None,
           "total_scanned": 0, "self_promoted": False, "error": None}
    oid = str(offer.get("id"))
    cat = offer.get("category_id"); city = offer.get("city_id"); region = offer.get("region_id")
    ckey = "%s|%s" % (oid, query or "")
    now = _dt.datetime.now().timestamp()
    
    # Read from SQLite POS cache
    _POS_TTL = 900
    try:
        c = storage.conn()
        cached_row = c.execute("SELECT ts, data_json FROM pos_cache WHERE ckey=?", (ckey,)).fetchone()
        c.close()
        if cached_row and (now - cached_row["ts"]) < _POS_TTL:
            return _json.loads(cached_row["data_json"])
    except Exception as e:
        print("pos_cache read error:", e)
    if _requests is None:
        res["error"] = "requests недоступен"; return res
    if not cat:
        res["error"] = "нет категории объявления"; return res

    organic = 0
    for page in range(max_pages):
        params = {"offset": page * per, "limit": per, "category_id": cat}
        if city:   params["city_id"] = city
        if region: params["region_id"] = region
        if query:  params["query"] = query
        try:
            resp = _requests.get("https://www.olx.kz/api/v1/offers/",
                                 headers=_PROMO_HEADERS, params=params, timeout=timeout)
        except Exception as e:
            res["error"] = "сеть: %s" % e; break
        if resp.status_code != 200:
            res["error"] = "HTTP %s" % resp.status_code; break
        try:
            body = resp.json() or {}
        except Exception:
            res["error"] = "не JSON"; break
        items = body.get("data") or []
        if not items:
            break
        promoted_idx = set((body.get("metadata") or {}).get("promoted") or [])
        for i, it in enumerate(items):
            res["total_scanned"] += 1
            is_slot = i in promoted_idx
            if str(it.get("id")) == oid:
                res["found"] = True
                res["page"] = page + 1
                if is_slot:
                    res["self_promoted"] = True
                else:
                    res["organic_rank"] = organic + 1
                    try:
                        c = storage.conn()
                        c.execute("INSERT INTO pos_cache(ckey, ts, data_json) VALUES(?,?,?) ON CONFLICT(ckey) DO UPDATE SET ts=excluded.ts, data_json=excluded.data_json", (ckey, now, _json.dumps(res)))
                        c.commit(); c.close()
                    except Exception as e:
                        print("pos_cache write error:", e)
                return res
            if not is_slot:
                organic += 1
                
    try:
        c = storage.conn()
        c.execute("INSERT INTO pos_cache(ckey, ts, data_json) VALUES(?,?,?) ON CONFLICT(ckey) DO UPDATE SET ts=excluded.ts, data_json=excluded.data_json", (ckey, now, _json.dumps(res)))
        c.commit(); c.close()
    except Exception as e:
        print("pos_cache write error:", e)
        
    return res

app = Flask(__name__)
try:
    storage.init()
except Exception as _e:
    print('storage.init deferred:', _e)

THEME = '''<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #0f1015;
  --panel: #15161c;
  --border: #23242f;
  --accent: #16c79a;
  --blue: #3d8bd9;
  --red: #ff5d5d;
  --yellow: #e0b341;
  --muted: #8b8b99;
  --text: #ffffff;
}
html, body {
  margin: 0; padding: 0;
  background: var(--bg); color: var(--muted);
  font-family: 'Inter', sans-serif;
  font-size: 13px;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
h2 {
  font-family: 'Montserrat', sans-serif;
  color: #fff;
  font-size: 22px;
  text-transform: uppercase;
  margin: 0 0 16px 0;
}
.kpi {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}
.kpi > div {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.kpi > div > b {
  font-size: 24px;
  color: #fff;
  font-family: 'Montserrat', sans-serif;
}
.rule, .muted { color: var(--muted); margin-bottom: 12px; font-size: 12px; }
.bar {
  display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 24px;
}
select, input, button {
  background: var(--panel);
  border: 1px solid var(--border);
  color: #fff;
  padding: 8px 12px;
  border-radius: 8px;
  font-family: 'Inter', sans-serif;
  font-size: 13px;
  outline: none;
}
select:hover, button:hover {
  border-color: var(--accent);
}
button {
  background: var(--accent);
  color: #000;
  font-weight: 600;
  cursor: pointer;
  border: none;
}
button:hover { background: #12a680; }
table {
  width: 100%; border-collapse: separate; border-spacing: 0;
  background: var(--panel);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--border);
}
th, td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid var(--border);
}
th {
  background: rgba(0,0,0,0.2);
  color: var(--muted);
  font-size: 11px;
  text-transform: uppercase;
  font-weight: 600;
}
td { color: #fff; }
tr:hover td { background: rgba(255,255,255,0.03); }
tr:last-child td { border-bottom: none; }
.num { text-align: right; }
.nav-links {
  display: flex; gap: 8px; margin-bottom: 24px;
}
.nav-links a {
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 500;
}
.nav-links a.active {
  background: var(--accent);
  color: #000;
  border-color: var(--accent);
}
</style>
<div style="max-width: 1400px; margin: 0 auto; padding: 24px;">
'''

SORTJS = """<script>
(function(){
 var ths=document.querySelectorAll('table thead th');
 ths.forEach(function(th,i){
   th.style.cursor='pointer'; th.title='Сортировать';
   th.addEventListener('click',function(){
     var tb=th.closest('table').tBodies[0];
     var rows=[].slice.call(tb.rows).filter(function(r){return r.cells.length>i;});
     var asc=th.getAttribute('data-asc')==='1';
     function num(s){var t=(s||'').replace(/\\s/g,'').replace(',','.').replace(/[^0-9.\\-]/g,'');var v=parseFloat(t);return isNaN(v)?null:v;}
     rows.sort(function(a,b){
       var x=a.cells[i].innerText.trim(), y=b.cells[i].innerText.trim();
       var nx=num(x), ny=num(y);
       if(nx!==null&&ny!==null) return asc?nx-ny:ny-nx;
       return asc?x.localeCompare(y,'ru'):y.localeCompare(x,'ru');
     });
     rows.forEach(function(r){tb.appendChild(r);});
     ths.forEach(function(t){t.textContent=t.textContent.replace(/[ \\u25BC\\u25B2]+$/,'');});
     th.textContent=th.textContent.replace(/[ \\u25BC\\u25B2]+$/,'')+(asc?' \\u25B2':' \\u25BC');
     th.setAttribute('data-asc', asc?'0':'1');
   });
 });
})();
</script>"""

PAGE = """<!doctype html><meta charset=utf-8><title>OLX бот — Главная панель</title>
{theme}
<div class='nav-links'>
    <a href='/' class='active'>Главная</a>
    <a href='/stats'>Вчерашняя</a>
    <a href='/weekly'>Еженедельная</a>
    <a href='/dashboard'>Дашборд</a>
    <a href='/bots'>Боты</a>
    <a href='/whatsapp'>WhatsApp бот</a>
    <a href='/logs'>Логи</a>
</div>

<h2>🏠 Управление аккаунтами OLX</h2>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin:14px 0 24px 0">
    <a href="/create" style="text-decoration:none"><button style="background:var(--accent);color:#000">➕ Создать объявление</button></a>
    <a href="/promo" style="text-decoration:none"><button style="background:var(--yellow);color:#000">🚀 Промо ABDU</button></a>
</div>

<div class="kpi" style="grid-template-columns: 1fr; max-width: 600px;">

    <div>
        <b style="font-size: 18px; margin-bottom: 8px;">➕ Добавить новый OLX аккаунт</b>
        <p class=muted style="font-size:13px; line-height:1.5;">Залогинься в OLX в текущем браузере (в соседней вкладке), придумай понятную метку для аккаунта и нажми «Авторизовать». Система привяжет его к аналитике.</p>
        <form action=/login method=get style="display:flex; gap:10px;">
            <input name=account placeholder="Например: Магазин 1" required style="flex:1; padding:8px; border-radius:6px; background:var(--bg); border:1px solid var(--border); color:#fff;">
            <button style="background:var(--accent);color:#000; padding:8px 16px; border-radius:6px; border:none; cursor:pointer; font-weight:bold;">Авторизовать в OLX</button>
        </form>
    </div>

    <div>
        <b style="font-size: 18px; margin-bottom: 8px;">✅ Подключённые аккаунты ({n})</b>
        <div style="display:flex; flex-direction:column; gap:8px;">
            {accs}
        </div>
    </div>
    
    <div>
        <button id=runBtn style="width:100%; padding:12px; font-size:14px;" onclick="startRun()">▶ Синхронизировать статистику (Запустить сбор сейчас)</button>
    </div>
</div>
"""

SCRIPT = """
<script>
function renameAcc(a){
  var n=prompt('Новая метка для '+a, a);
  if(!n||n===a) return;
  var f=new FormData(); f.append('account',a); f.append('newname',n.trim());
  fetch('/rename',{method:'POST',body:f}).then(function(){location.reload();});
}
function startRun(){
  var b=document.getElementById('runBtn');
  if(b.disabled) return;
  b.disabled=true; b.style.background='#9aa7b2';
  fetch('/run',{method:'POST'}).catch(function(){});
  var ac; try{ ac=new (window.AudioContext||window.webkitAudioContext)(); }catch(e){}
  var t=120;
  function tick(){
    var m=Math.floor(t/60), sec=('0'+(t%60)).slice(-2);
    if(t>0){ b.textContent='\u23F3 \u0421\u0431\u043E\u0440 \u0438\u0434\u0451\u0442... '+m+':'+sec; }
    else{
      clearInterval(iv);
      b.disabled=false; b.style.background='#16c79a';
      b.textContent='\u2705 \u0413\u043E\u0442\u043E\u0432\u043E! \u041E\u0442\u043A\u0440\u044B\u0442\u044C \u0441\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043A\u0443';
      b.onclick=function(){location.href='/stats';};
      if(ac){try{var o=ac.createOscillator(),g=ac.createGain();o.connect(g);g.connect(ac.destination);o.frequency.value=880;g.gain.value=0.12;o.start();setTimeout(function(){o.stop();},450);}catch(e){}}
    }
    t--;
  }
  tick(); var iv=setInterval(tick,1000);
}
</script>
"""


@app.get("/")
def home():
    accs = auth._load()
    rows = "".join(
        f"<div class=acc>✓ {a}"
        f"<span style='float:right'>"
        f"<button type=button onclick=\"renameAcc('{a}')\" style='padding:3px 11px;font-size:12px'>переименовать</button> "
        f"<form style='display:inline' method=post action=/delete>"
        f"<input type=hidden name=account value='{a}'>"
        f"<button style='padding:3px 11px;font-size:12px;background:#ff5d5d;border-color:#ff5d5d'>удалить</button>"
        f"</form></span></div>" for a in accs) or "<i>пока нет</i>"
    return PAGE.format(n=len(accs), accs=rows, theme=THEME) + SCRIPT

@app.get("/login")
def login():
    if not config.CLIENT_ID or not config.CLIENT_SECRET:
        return """
        <div style="font-family:system-ui; max-width:500px; margin: 50px auto; padding: 20px; border: 1px solid #ff4444; border-radius: 8px; background: #1a0f0f; color: #ff6b6b;">
            <h3 style="margin-top:0;">Ошибка конфигурации Partner API</h3>
            <p>В вашем файле <code>.env</code> (или переменных окружения) не заполнены ключи <b>OLX_CLIENT_ID</b> и <b>OLX_CLIENT_SECRET</b>.</p>
            <p>Для подключения аккаунта к аналитике через официальный API:</p>
            <ol style="padding-left:20px; line-height:1.6;">
                <li>Зарегистрируйтесь на <a href="https://developer.olx.kz/" target="_blank" style="color:#00e676;">developer.olx.kz</a>.</li>
                <li>Заполните вкладку <b>Partner details</b> и примите соглашение.</li>
                <li>Создайте приложение и получите <b>client_id</b> и <b>client_secret</b>.</li>
                <li>Впишите их в файл <code>.env</code> в корне проекта.</li>
            </ol>
            <p>После этого перезапустите сервер и попробуйте снова.</p>
            <a href="/" style="display:inline-block; margin-top:15px; color:#00e676; text-decoration:none; font-weight:bold;">← Назад к панели</a>
        </div>
        """, 400
    account = request.args.get("account", "default")
    return redirect(auth.build_authorize_url(state=account))

@app.get("/olx/callback")
def callback():
    err = request.args.get("error")
    if err:
        return f"<h3 style='font-family:system-ui'>Отказано: {err}</h3>", 400
    code = request.args.get("code")
    account = request.args.get("state", "default")
    try:
        auth.exchange_code(code, account)
    except Exception as e:
        return f"<h3 style='font-family:system-ui'>Ошибка обмена кода: {e}</h3>", 500
    return (f"<h3 style='font-family:system-ui;color:#16c79a'>Аккаунт «{account}» подключён ✓</h3>"
            f"<p style='font-family:system-ui'><a href='/'>← назад к панели</a></p>")

@app.get("/debug")
def debug():
    accs = runner.accounts()
    if not accs:
        return jsonify({"error":"нет аккаунтов"})
    cl = OlxClient(accs[0])
    out = {"account": accs[0]}
    rows = storage.latest_rows()
    out["sample_stored_city"] = [{"title":(r["title"] or "")[:30], "city_stored": r["city"]} for r in rows[:3]]
    out["cities_cached_count"] = len(storage.city_names())
    try:
        c = cl._req("GET", "/cities/1")
        out["cities_1_raw"] = c
    except Exception as e:
        out["cities_1_error"] = str(e)
    try:
        cat_id = rows[0]["category_id"] if rows else None
        out["category_raw"] = cl._req("GET", f"/categories/{cat_id}") if cat_id else None
        out["category_kinds_cached"] = sum(1 for v in storage.category_kinds().values() if v)
    except Exception as e:
        out["category_error"] = str(e)
    # --- сканируем платные опции по первым объявлениям ---
    pf_sample=None; pf_active=[]
    for r in rows[:15]:
        try:
            pf = cl._req("GET", f"/adverts/{r['id']}/paid-features")
            if pf_sample is None: pf_sample={"id":r["id"],"title":(r["title"] or "")[:30],"raw":pf}
            data = pf.get("data", pf) if isinstance(pf, dict) else pf
            if data: pf_active.append({"id":r["id"],"title":(r["title"] or "")[:30],"raw":pf})
        except Exception as e:
            out["paid_features_error"]=str(e); break
    out["paid_features_sample"]=pf_sample
    out["paid_features_active_count"]=len(pf_active)
    out["paid_features_active"]=pf_active[:3]
    try: out["paid_features_catalog"]=cl._req("GET","/paid-features")
    except Exception as e: out["paid_features_catalog_error"]=str(e)
    # --- чаты: структура для автоответчика ---
    try:
        th = cl._req("GET", "/threads")
        tdata = th.get("data", th) if isinstance(th, dict) else th
        out["threads_count"] = len(tdata or [])
        if tdata:
            t0 = tdata[0]; out["thread_sample"] = t0
            tid = t0.get("id")
            out["messages_sample"] = cl._req("GET", f"/threads/{tid}/messages")
    except Exception as e:
        out["threads_error"] = str(e)
    return jsonify(out)


import subprocess


import subprocess
import json


@app.post("/whatsapp_login")
def whatsapp_login_endpoint():
    import subprocess
    try:
        subprocess.Popen(["python", "whatsapp_login.py"], shell=False)
        return jsonify({"status": "запущено"})
    except Exception as e:
        return jsonify({"status": "ошибка", "error": str(e)})

@app.post("/whatsapp_send")
def whatsapp_send_now():
    try:
        data = request.get_json(silent=True) or {}
        limit = data.get("limit", 0)
        subprocess.Popen(["python", "whatsapp_sender.py", str(limit)], shell=False)
        return jsonify({"status": "запущено"})
    except Exception as e:
        return jsonify({"status": "ошибка", "error": str(e)})

from flask import send_from_directory
@app.get("/media/<path:filename>")
def serve_media(filename):
    import os
    if not os.path.exists("media"):
        os.makedirs("media")
    return send_from_directory("media", filename)


@app.post("/whatsapp/sync_google")
def whatsapp_sync_google():
    sheet_url = request.form.get("sheet_url", "")
    if not sheet_url:
        return redirect("/whatsapp")
        
    try:
        # Извлекаем ID из ссылки
        import re
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", sheet_url)
        if not match:
            return "Неверная ссылка на Google Таблицу", 400
        spreadsheet_id = match.group(1)
        
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        
        # Получаем имя первого листа
        sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get('sheets', '')
        first_sheet_name = sheets[0].get("properties", {}).get("title", "Лист1")
        
        # Получаем данные
        result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=f"'{first_sheet_name}'!A:Z").execute()
        values = result.get('values', [])
        
        groups = load_whatsapp_groups()
        existing_urls = {g.get('url', '') for g in groups}
        
        added = 0
        for i, row in enumerate(values):
            if not row: continue
            
            # Ищем ссылку
            url = ""
            name = ""
            for cell in row:
                if isinstance(cell, str) and "chat.whatsapp.com" in cell:
                    url = cell.strip()
                    break
            
            if url:
                # Если в строке есть еще текст, возьмем его как имя
                for cell in row:
                    if cell != url and len(cell) > 2:
                        name = cell.strip()
                        break
                        
                if url not in existing_urls:
                    groups.append({
                        "name": name,
                        "url": url,
                        "status": "pending",
                        "reason": "",
                        "row_index": i + 1  # 1-based index in Google Sheets
                    })
                    existing_urls.add(url)
                    added += 1
                    
        save_whatsapp_groups(groups)
        
        # Сохраняем последнюю ссылку и данные таблицы чтобы sender мог туда писать
        config_data = load_whatsapp_config()
        config_data["last_sheet_url"] = sheet_url
        config_data["google_sheet_id"] = spreadsheet_id
        config_data["google_sheet_name"] = first_sheet_name
        
        with open("config_whatsapp.json", "w", encoding="utf-8") as f:
            import json
            json.dump(config_data, f, ensure_ascii=False, indent=4)
            
    except Exception as e:
        return f"Ошибка при синхронизации с Google: {e}", 500
        
    return redirect("/whatsapp")

@app.post("/whatsapp/save_templates")
def whatsapp_save_templates():
    import os
    if not os.path.exists("media"):
        os.makedirs("media")
        
    config_file = "config_whatsapp.json"
    data = load_whatsapp_config()
    
    action = request.form.get("action", "save")
    
    if "templates" not in data or not isinstance(data["templates"], list):
        data["templates"] = [{"text": data.get("text_template", ""), "media": ""}]
        
    if action == "add":
        data["templates"].append({"text": "", "media": ""})
    elif action.startswith("del_"):
        idx = int(action.split("_")[1])
        if 0 <= idx < len(data["templates"]):
            media_path = data["templates"][idx].get("media")
            if media_path and os.path.exists(media_path):
                try: os.remove(media_path)
                except: pass
            data["templates"].pop(idx)
    elif action.startswith("delmedia_"):
        idx = int(action.split("_")[1])
        if 0 <= idx < len(data["templates"]):
            media_path = data["templates"][idx].get("media")
            if media_path and os.path.exists(media_path):
                try: os.remove(media_path)
                except: pass
            data["templates"][idx]["media"] = ""
    else:
        # Update existing
        new_templates = []
        for i in range(len(data["templates"])):
            text = request.form.get(f"template_text_{i}", "")
            old_media = data["templates"][i].get("media", "")
            
            # Check for new file upload
            file_key = f"media_{i}"
            new_media = old_media
            if file_key in request.files:
                file = request.files[file_key]
                if file.filename != '':
                    ext = os.path.splitext(file.filename)[1]
                    file_path = os.path.join("media", f"template_{i}{ext}")
                    file.save(file_path)
                    new_media = file_path
                    
            new_templates.append({"text": text, "media": new_media})
        data["templates"] = new_templates
        
        # Select active
        active_idx = request.form.get("active_template", "0")
        data["active_template"] = int(active_idx) if active_idx.isdigit() else 0
        
        if data["templates"] and 0 <= data["active_template"] < len(data["templates"]):
            data["text_template"] = data["templates"][data["active_template"]]["text"]
            
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    return redirect("/whatsapp")

@app.get("/whatsapp")
def whatsapp_page():
    config_data = load_whatsapp_config()
    
    if "templates" not in config_data or not isinstance(config_data["templates"], list):
        config_data["templates"] = [{"text": config_data.get("text_template", ""), "media": ""}]
        
    active_idx = config_data.get("active_template", 0)
    if active_idx >= len(config_data["templates"]):
        active_idx = 0
        
    templates_html = ""
    for i, tpl in enumerate(config_data["templates"]):
        is_active = (i == active_idx)
        border_color = "var(--accent)" if is_active else "var(--border)"
        bg_active = "rgba(0, 255, 136, 0.05)" if is_active else "var(--bg)"
        media_path = tpl.get("media", "")
        
        media_html = ""
        if media_path:
            file_name = os.path.basename(media_path)
            ext = os.path.splitext(file_name)[1].lower()
            preview = ""
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                preview = f'<img src="/media/{file_name}" style="max-height: 80px; max-width: 120px; border-radius: 4px; object-fit: cover;">'
            elif ext in ['.mp4', '.avi', '.mov', '.webm']:
                preview = f'<video src="/media/{file_name}" style="max-height: 80px; max-width: 120px; border-radius: 4px; object-fit: cover;" muted autoplay loop></video>'
                
            media_html = f"""
            <div style="margin-top: 10px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 6px; display: flex; align-items: center; justify-content: space-between; gap: 10px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    {preview}
                    <div style="font-size: 12px; color: var(--blue);">📎 <b>{file_name}</b></div>
                </div>
                <button type="submit" name="action" value="delmedia_{i}" style="background: none; border: none; color: var(--danger); cursor: pointer; font-size: 12px; font-weight: bold;">Удалить</button>
            </div>
            """
            
        templates_html += f"""
        <div style="border: 1px solid {border_color}; border-radius: 8px; padding: 12px; margin-bottom: 16px; background: {bg_active}; position: relative;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <label style="display: flex; align-items: center; gap: 8px; font-weight: bold; cursor: pointer;">
                    <input type="radio" name="active_template" value="{i}" {'checked' if is_active else ''} style="width: 16px; height: 16px; accent-color: var(--accent);">
                    Шаблон {i+1} {'<span style="color:var(--accent); font-size:11px;">(активный)</span>' if is_active else ''}
                </label>
                <button type="submit" name="action" value="del_{i}" style="background: none; border: none; color: var(--danger); cursor: pointer; font-size: 13px;" onclick="return confirm('Удалить этот шаблон целиком?')">🗑 Удалить</button>
            </div>
            <textarea name="template_text_{i}" required style="width: 100%; min-height: 80px; box-sizing: border-box; padding: 10px; background: rgba(0,0,0,0.2); border: 1px solid var(--border); color: #fff; border-radius: 4px; font-family: inherit; font-size: 13px; resize: vertical; margin-bottom: 8px;">{tpl.get('text', '')}</textarea>
            
            <div style="display: flex; flex-direction: column; gap: 4px;">
                <label style="font-size: 12px; font-weight: bold; color: var(--muted);">Прикрепить фото/видео (оставьте пустым чтобы сохранить текущее):</label>
                <input type="file" name="media_{i}" accept="image/*,video/*" style="font-size: 12px; color: #fff;">
            </div>
            {media_html}
        </div>
        """

    groups_data = load_whatsapp_groups()
    groups_rows = ""
    success_count = 0
    error_count = 0
    waiting_count = 0
    
    for g in groups_data:
        bg_color = "rgba(255,255,255,0.02)"
        st_text = "⏳ Ожидает"
        if g.get('status') == 'success':
            bg_color = "rgba(0, 255, 0, 0.1)"
            st_text = "✅ Успешно"
            success_count += 1
        elif g.get('status') == 'error':
            bg_color = "rgba(255, 0, 0, 0.1)"
            st_text = "❌ Ошибка"
            error_count += 1
        else:
            waiting_count += 1
            
        groups_rows += f"""
        <tr style="background: {bg_color}; border-bottom: 1px solid var(--border);">
            <td style="padding: 10px;">{g.get('name', 'Без названия')}</td>
            <td style="padding: 10px;"><a href="{g.get('url', '')}" target="_blank" style="color:var(--blue); text-decoration:none;">{g.get('url', '')}</a></td>
            <td style="padding: 10px; font-weight: bold;">{st_text}</td>
            <td style="padding: 10px; color: var(--muted); font-size: 12px;">{g.get('reason', '')}</td>
        </tr>
        """

    custom_html = f"""
    <h2>💬 WhatsApp Рассылка по группам</h2>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 24px; margin-top: 20px;">
        
        <!-- Левая колонка: шаблоны -->
        <div style="background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                <h3 style="color: var(--accent); font-size: 16px; margin: 0;">📝 Шаблоны рассылки</h3>
            </div>
            
            <form action="/whatsapp/save_templates" method="POST" enctype="multipart/form-data">
                {templates_html}
                
                <div style="display: flex; gap: 10px; margin-top: 20px;">
                    <button type="submit" name="action" value="save" style="flex: 2; padding: 12px; font-size: 14px; border-radius: 6px; background: var(--accent); color: #000; font-weight: 700; border: none; cursor: pointer; transition: 0.2s;">💾 Сохранить и выбрать</button>
                    <button type="submit" name="action" value="add" style="flex: 1; padding: 12px; font-size: 14px; border-radius: 6px; background: rgba(255,255,255,0.1); color: #fff; font-weight: 700; border: 1px solid var(--border); cursor: pointer; transition: 0.2s;">➕ Добавить</button>
                </div>
            </form>
        </div>
        
        <!-- Правая колонка: статус и запуск -->
        <div style="background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; gap: 24px;">
            <div>
                <h3 style="margin-bottom: 16px; color: var(--accent); font-size: 16px;">📊 Статус базы</h3>
                
                <div style="background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 16px; font-family: monospace; font-size: 13px; line-height: 1.6;">
                    <div style="font-weight: bold; border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 8px; color: var(--blue); font-size: 14px;">Статистика по текущей базе:</div>
                    <div style="margin-bottom: 6px;">Всего групп: <span style="color:#fff; font-weight:bold;">{len(groups_data)}</span></div>
                    <div style="margin-bottom: 6px;">Ожидают отправки: <span style="color:#fff; font-weight:bold;">{waiting_count}</span></div>
                    <div style="margin-bottom: 6px;">Успешно отправлено: <span style="color:var(--accent); font-weight:bold;">{success_count}</span></div>
                    <div style="margin-bottom: 6px;">Ошибок (не удалось): <span style="color:var(--danger); font-weight:bold;">{error_count}</span></div>
                </div>
            </div>
            
            <div>
                <h3 style="margin-bottom: 16px; color: var(--accent); font-size: 16px;">🚀 Управление рассылкой</h3>
                <div style="display: flex; gap: 12px; flex-wrap: wrap; align-items: center; margin-bottom: 8px;">
                    <button onclick="runLogin()" style="flex: 1; min-width: 150px; padding: 14px; font-size: 14px; border-radius: 6px; background: var(--blue); color: #fff; font-weight: bold; border: none; cursor: pointer; transition: 0.2s;">🔑 Подключить WhatsApp</button>
                    <div style="display: flex; align-items: center; gap: 8px; flex: 1; min-width: 150px;">
                        <input type="number" id="send-limit" placeholder="Лимит (0 - все)" min="0" value="0" style="width: 80px; padding: 12px; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; color: #fff; font-size: 13px; text-align: center;" title="Сколько групп обойти за этот запуск (0 - без лимита)">
                        <button onclick="runSender()" style="flex: 1; padding: 14px; font-size: 14px; border-radius: 6px; background: var(--danger); color: #fff; font-weight: bold; border: none; cursor: pointer; transition: 0.2s;">🚀 Запустить рассылку</button>
                    </div>
                </div>
                <div id="run-status" style="margin-top: 16px; padding: 12px; border-radius: 6px; background: rgba(255, 255, 255, 0.02); border: 1px dashed var(--border); text-align: center; font-size: 13px; color: var(--muted); font-weight: bold; display: none;">
                    Открывается браузер...
                </div>
            </div>
        </div>
    </div>
    
    <div style="background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-top: 24px;">
        <h3 style="margin-bottom: 16px; color: var(--accent); font-size: 16px;">📂 База групп для рассылки (Google Таблицы или CSV)</h3>
        
        <div style="display: flex; gap: 24px; flex-wrap: wrap; margin-bottom: 20px;">
            <!-- Левая часть: Google Tables -->
            <form action="/whatsapp/sync_google" method="POST" style="flex: 1; min-width: 300px; background: rgba(0,255,136,0.05); padding: 16px; border-radius: 8px; border: 1px dashed var(--accent);">
                <div style="font-weight: bold; margin-bottom: 10px; color: var(--accent);">📊 Загрузить из Google Таблицы</div>
                <div style="display: flex; gap: 10px;">
                    <input type="text" name="sheet_url" value="{config_data.get('last_sheet_url', '')}" placeholder="Вставьте ссылку на Google Таблицу..." required style="padding: 10px; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; color: #fff; flex: 1; font-size: 13px;">
                    <button type="submit" style="padding: 10px 16px; font-size: 13px; border-radius: 6px; background: var(--accent); color: #000; font-weight: bold; border: none; cursor: pointer; transition: 0.2s; white-space: nowrap;">🔄 Синхронизировать</button>
                </div>
                <div style="font-size: 11px; color: var(--muted); margin-top: 6px;">Бот сам найдет колонку со ссылками (chat.whatsapp.com) в первом листе. Доступ к таблице должен быть открыт для сервисного аккаунта.</div>
            </form>
            
            <!-- Правая часть: CSV -->
            <form action="/whatsapp/upload_csv" method="POST" enctype="multipart/form-data" style="flex: 1; min-width: 300px; background: rgba(255,255,255,0.02); padding: 16px; border-radius: 8px; border: 1px dashed var(--border);">
                <div style="font-weight: bold; margin-bottom: 10px; color: var(--muted);">📁 Или загрузить CSV файл</div>
                <div style="display: flex; gap: 10px;">
                    <input type="file" name="csv_file" accept=".csv,.txt" required style="padding: 8px; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; color: #fff; flex: 1; font-size: 13px;">
                    <button type="submit" style="padding: 10px 16px; font-size: 13px; border-radius: 6px; background: var(--blue); color: #fff; font-weight: bold; border: none; cursor: pointer; transition: 0.2s; white-space: nowrap;">📥 Загрузить файл</button>
                </div>
            </form>
        </div>
        
        <div style="margin-bottom: 16px; text-align: right;">
            <a href="/whatsapp/clear_csv" style="padding: 8px 16px; font-size: 12px; border-radius: 6px; background: var(--danger); color: #fff; font-weight: bold; border: none; cursor: pointer; text-decoration: none; transition: 0.2s;" onclick="return confirm('Вы уверены что хотите очистить ВСЮ базу групп?')">🗑 Очистить текущую базу</a>
        </div>
        
        <div style="overflow-x: auto; max-height: 400px;">
            <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 13px;">
                <thead style="position: sticky; top: 0; background: var(--bg);">
                    <tr style="border-bottom: 2px solid var(--border);">
                        <th style="padding: 10px;">ЖК / Название</th>
                        <th style="padding: 10px;">Ссылка</th>
                        <th style="padding: 10px;">Статус</th>
                        <th style="padding: 10px;">Причина / Заметка</th>
                    </tr>
                </thead>
                <tbody>
                    {groups_rows if groups_rows else '<tr><td colspan="4" style="padding: 16px; text-align: center; color: var(--muted);">Нет данных. Сохраните таблицу Excel как CSV и загрузите её.</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function runLogin() {{
            const statusDiv = document.getElementById("run-status");
            statusDiv.style.display = "block";
            statusDiv.style.borderColor = "var(--blue)";
            statusDiv.style.color = "var(--blue)";
            statusDiv.innerText = "Открываем браузер для привязки WhatsApp...";
            
            fetch("/whatsapp_login", {{ method: "POST" }})
                .then(res => res.json())
                .then(data => {{
                    if(data.status === "запущено") {{
                        statusDiv.innerText = "Браузер открыт! Отсканируйте QR-код. Окно само закроется после входа.";
                        statusDiv.style.color = "var(--accent)";
                        statusDiv.style.borderColor = "var(--accent)";
                    }} else {{
                        statusDiv.innerText = "Ошибка: " + data.error;
                    }}
                }});
        }}
        function runSender() {{
            const statusDiv = document.getElementById("run-status");
            statusDiv.style.display = "block";
            statusDiv.style.borderColor = "var(--blue)";
            statusDiv.style.color = "var(--blue)";
            statusDiv.innerText = "Запускаем скрипт рассылки... Сейчас откроется окно браузера!";
            
            fetch("/whatsapp_send", {{ method: "POST" }})
                .then(res => res.json())
                .then(data => {{
                    if(data.status === "запущено") {{
                        statusDiv.innerText = "Скрипт запущен! Посмотрите на панель задач, там должен появиться новый браузер.";
                        statusDiv.style.color = "var(--accent)";
                        statusDiv.style.borderColor = "var(--accent)";
                        setInterval(() => window.location.reload(), 5000);
                    }} else {{
                        statusDiv.innerText = "Ошибка запуска: " + data.error;
                        statusDiv.style.color = "var(--danger)";
                        statusDiv.style.borderColor = "var(--danger)";
                    }}
                }})
                .catch(err => {{
                    statusDiv.innerText = "Ошибка запуска: " + err;
                    statusDiv.style.color = "var(--danger)";
                    statusDiv.style.borderColor = "var(--danger)";
                }});
        }}
    </script>
    """
    
    page_html = (
        THEME + 
        "<title>WhatsApp бот рассылка</title>"
        "<div class='nav-links'>"
        "    <a href='/'>Главная</a>"
        "    <a href='/stats'>Вчерашняя</a>"
        "    <a href='/weekly'>Еженедельная</a>"
        "    <a href='/dashboard'>Дашборд</a>"
        "    <a href='/bots'>Боты</a>"
        "    <a href='/whatsapp' class='active'>WhatsApp бот</a>"
        "    <a href='/logs'>Логи</a>"
        "</div>" +
        custom_html +
        "</div>"
    )
    return page_html

@app.post("/whatsapp/upload_csv")
def whatsapp_upload_csv():
    import csv
    if 'csv_file' not in request.files:
        return redirect("/whatsapp")
        
    file = request.files['csv_file']
    if file.filename == '':
        return redirect("/whatsapp")
        
    if file:
        content_bytes = file.read()
        try:
            content_str = content_bytes.decode('utf-8')
        except:
            content_str = content_bytes.decode('cp1251', errors='replace')
            
        lines = content_str.splitlines()
        
        delimiter = ','
        if lines and ';' in lines[0] and lines[0].count(';') > lines[0].count(','):
            delimiter = ';'
            
        reader = csv.reader(lines, delimiter=delimiter)
        groups = []
        for i, row in enumerate(reader):
            if i == 0 or len(row) < 3:
                continue 
            
            name = row[1].strip() if len(row) > 1 else ""
            url = row[2].strip() if len(row) > 2 else ""
            if not url.startswith("http"):
                continue
                
            groups.append({
                "id": i,
                "name": name,
                "url": url,
                "platform": row[3] if len(row) > 3 else "WhatsApp",
                "status": "waiting",
                "reason": ""
            })
            
        save_whatsapp_groups(groups)
        
    return redirect("/whatsapp")

@app.get("/whatsapp/clear_csv")
def whatsapp_clear_csv():
    save_whatsapp_groups([])
    return redirect("/whatsapp")

@app.post("/whatsapp/save")
def whatsapp_save():
    enabled = request.form.get("enabled") == "1"
    interval = request.form.get("interval", "15")
    wa_number = request.form.get("wa_number", "").strip()
    text_template = request.form.get("text_template", "").strip()
    since_date = request.form.get("since_date", "").strip()
    
    config_data = {
        "enabled": "1" if enabled else "0",
        "interval": interval,
        "wa_number": wa_number,
        "text_template": text_template,
        "since_date": since_date
    }
    
    save_whatsapp_config(config_data)
    update_scheduler_jobs()
    return redirect("/whatsapp")

@app.post("/rename")
def rename_account():
    old = request.form.get("account"); new = (request.form.get("newname") or "").strip()
    data = auth._load()
    if old in data and new and new not in data:
        data[new] = data.pop(old); auth._save(data)
        storage.rename_account(old, new)
    return redirect("/")

@app.post("/delete")
def delete_account():
    acc = request.form.get("account")
    data = auth._load()
    if acc in data:
        del data[acc]
        auth._save(data)
    return redirect("/")

@app.post("/run")
def run_now():
    threading.Thread(target=runner.run_all, daemon=True).start()
    return redirect("/")

@app.get("/status")
def status():
    return jsonify({"accounts": runner.accounts()})


@app.get("/autoextend")
def autoextend_diag():
    """Read-only диагностика: у каждого объявления показываем auto_extend_enabled,
    valid_to, activated_at, created_at, status. ?detail=1 — дотянуть полное объявление,
    если поле пустое в списке (медленнее). ?acc=<метка> — только один кабинет."""
    detail = request.args.get("detail") == "1"
    only = request.args.get("acc")
    accs = [only] if only else runner.accounts()
    out, on, off, unknown = {}, 0, 0, 0
    for acc in accs:
        cl = OlxClient(acc)
        try:
            ads = cl.all_adverts()
        except Exception as e:
            out[acc] = {"error": str(e)}
            continue
        rows = []
        for a in (ads or []):
            ae = a.get("auto_extend_enabled")
            if detail and ae is None and a.get("id"):
                try:
                    full = cl.advert(a["id"])
                    full = full.get("data", full) if isinstance(full, dict) else full
                    if full:
                        a = full
                        ae = a.get("auto_extend_enabled")
                except Exception:
                    pass
            if ae is True:
                on += 1
            elif ae is False:
                off += 1
            else:
                unknown += 1
            rows.append({
                "id": a.get("id"),
                "title": (a.get("title") or "")[:44],
                "status": a.get("status"),
                "auto_extend": ae,
                "valid_to": a.get("valid_to"),
                "activated_at": a.get("activated_at"),
                "created_at": a.get("created_at"),
            })
        out[acc] = {"count": len(rows), "adverts": rows}
    out["_summary"] = {"auto_extend_on": on, "auto_extend_off": off, "unknown": unknown,
                       "подсказка": "если auto_extend всюду null — добавь ?detail=1"}
    return jsonify(out)


def _kind_from_root(root):
    r = (root or "").lower()
    if "услуг" in r: return "услуга"
    if "работа" in r or "ваканс" in r: return "вакансия"
    return "товар"

def _resolve_categories(ids):
    have = storage.category_names(); kinds = storage.category_kinds(); rubs = storage.category_rubrics()
    missing = [i for i in ids if i and (i not in have or kinds.get(i) is None or not rubs.get(i))]
    accs = runner.accounts()
    if missing and accs:
        cl = OlxClient(accs[0])
        for cid in missing:
            leaf=f"кат.{cid}"; root=None; cur=cid; seen=set()
            for _ in range(8):
                if cur in seen: break
                seen.add(cur)
                try:
                    c = cl._req("GET", f"/categories/{cur}") or {}
                    c = c.get("data", c) if isinstance(c, dict) else c
                except Exception:
                    break
                nm = (c or {}).get("name") or (c or {}).get("title")
                if cur==cid and nm: leaf=nm
                if nm: root=nm
                parent = (c or {}).get("parent_id") or (c or {}).get("parentId")
                if not parent: break
                cur=parent
            storage.save_category(cid, leaf, _kind_from_root(root), root)
    return storage.category_names()

def _resolve_cities(ids):
    have = storage.city_names()
    missing = [i for i in ids if isinstance(i,int) and i not in have]
    if missing:
        accs = runner.accounts()
        if accs:
            cl = OlxClient(accs[0])
            for cid in missing:
                try:
                    c = cl._req("GET", f"/cities/{cid}") or {}
                    c = c.get("data", c) if isinstance(c, dict) else c
                    name = (c or {}).get("name") or (c or {}).get("title") or f"city {cid}"
                except Exception:
                    name = f"city {cid}"
                storage.save_city(cid, name)
    return storage.city_names()

def _rows_filtered():
    rows = storage.latest_rows()
    cats = _resolve_categories({r["category_id"] for r in rows})
    def _cid(v):
        try: return int(v)
        except (TypeError, ValueError): return v
    city_ids = {c for c in (_cid(r["city"]) for r in rows) if isinstance(c, int)}
    cities = _resolve_cities(city_ids)
    kinds = storage.category_kinds(); rubrics = storage.category_rubrics()
    for r in rows:
        r["service"] = cats.get(r["category_id"], f"кат.{r['category_id']}")
        r["kind"] = kinds.get(r["category_id"]) or ""
        r["rubric"] = rubrics.get(r["category_id"]) or ""
        cid = _cid(r["city"])
        if isinstance(cid, int):
            r["city"] = cities.get(cid) or str(cid)
        else:
            r["city"] = cid or ""
    city = request.args.get("city","")
    acc  = request.args.get("account","")
    svc  = request.args.get("service","")
    kind = request.args.get("kind","")
    out = [r for r in rows
           if (not city or (r["city"] or "")==city)
           and (not acc or r["account"]==acc)
           and (not svc or r["service"]==svc)
           and (not kind or r["kind"]==kind)]
    return rows, out

STATS = """<!doctype html><meta charset=utf-8><title>Вчерашняя статистика</title>
{theme}
<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:6px"><h2 style="margin:0">📊 Вчерашняя статистика <span style="font-size:14px;font-weight:400;color:var(--muted)">&nbsp;<a href="/">🏠 Главная</a> · <a href="/weekly">📅 Еженедельная</a></span></h2><a href="/stats.csv{qs}"><button type=button>⬇ Скачать CSV</button></a></div>
<form class=bar method=get>
<select name=city onchange="this.form.submit()"><option value="">Все города</option>{cities}</select>
<select name=account onchange="this.form.submit()"><option value="">Все кабинеты</option>{accounts}</select>
<select name=service onchange="this.form.submit()"><option value="">Все услуги</option>{services}</select>
</form>
<div class=kpi>
<div>Объявлений<b>{n}</b></div>
<div>Просмотры<b>{views}</b></div>
<div>Звонки (тел)<b>{phones}</b></div>
<div>Чат-лиды<b>{chats}</b></div>
<div>👁 Просм. за день<b style="color:#16c79a">{views_day}</b></div>
<div>📞 Звонки за день<b style="color:#16c79a">{phones_day}</b></div>
</div>
<table><thead><tr><th>Кабинет</th><th>Услуга</th><th>Город</th><th>Объявление</th><th>ID</th>
<th class=num>👁 Просм.</th><th class=num>+дн</th><th class=num>📞 Тел.</th><th class=num>+дн</th><th class=num>💬 Чат</th><th>Действие</th></tr></thead>
<tbody>{tbody}</tbody></table>"""

def _opts(values, sel):
    return "".join(f'<option value="{v}"{" selected" if v==sel else ""}>{v}</option>' for v in values)

@app.get("/stats")
def stats_page():
    allrows, rows = _rows_filtered()
    cities   = sorted({r["city"] for r in allrows if r["city"]})
    accounts = sorted({r["account"] for r in allrows})
    services = sorted({r["service"] for r in allrows})
    kind_opts = "".join(
        f'<option value="{k}"{" selected" if k==request.args.get("kind","") else ""}>{lbl}</option>'
        for k,lbl in [("услуга","🛠 Услуга"),("товар","📦 Товар"),("вакансия","💼 Вакансия")])
    try:
        _wi,_wa,_wb=_weekly_data("prev"); dead_ids={it["id"] for it in _wi if it.get("dead")}
    except Exception:
        dead_ids=set()
    body=""
    def _d(now, prev):
        if prev is None: return "—"
        d=(now or 0)-(prev or 0)
        return ("+%d"%d) if d>0 else ("0" if d==0 else str(d))
    for r in rows:
        idcell=("<a href='%s' rel='noopener' style='font-family:monospace'>%s ↗</a>"%(r["url"],r["id"])) if r.get("url") else ("<span style='font-family:monospace'>%s</span>"%r["id"])
        act=("<button onclick=\"deact(%s,'%s',this)\" style='padding:4px 9px;font-size:12px;background:#3a1414;border:1px solid #5a1f1f;color:#ff9d9d;border-radius:7px;cursor:pointer'>🪦 Отключить</button>"%(r["id"],r["account"])) if r["id"] in dead_ids else "—"
        body+=("<tr><td>%s</td><td>%s</td><td>%s</td>"
               "<td><a href='/advert/%s'>%s</a></td>"
               "<td class=muted>%s</td>"
               "<td class=num>%s</td><td class=num style='color:#16c79a'>%s</td>"
               "<td class=num>%s</td><td class=num style='color:#16c79a'>%s</td>"
               "<td class=num>%s</td><td>%s</td></tr>") % (
            r["account"], r.get("service",""), r["city"] or "—",
            r["id"], (r["title"] or "")[:70], idcell,
            r["advert_views"] or 0, _d(r.get("advert_views"), r.get("prev_views")),
            r["phone_views"] or 0, _d(r.get("phone_views"), r.get("prev_phone")),
            r["threads"] or 0, act)
    import urllib.parse as up
    qs = "?"+up.urlencode({k:v for k,v in request.args.items()}) if request.args else ""
    _signed = lambda d: ("+%d" % d) if d >= 0 else str(d)
    return STATS.format(
        theme=THEME,
        qs=qs,
        kinds=kind_opts,
        cities=_opts(cities, request.args.get("city","")),
        accounts=_opts(accounts, request.args.get("account","")),
        services=_opts(services, request.args.get("service","")),
        n=len(rows),
        views=sum(r["advert_views"] or 0 for r in rows),
        phones=sum(r["phone_views"] or 0 for r in rows),
        chats=sum(r["threads"] or 0 for r in rows),
        views_day=_signed(sum((r["advert_views"] or 0)-(r["prev_views"] or 0) for r in rows if r.get("prev_views") is not None)),
        phones_day=_signed(sum((r["phone_views"] or 0)-(r["prev_phone"] or 0) for r in rows if r.get("prev_phone") is not None)),
        tbody=body or "<tr><td colspan=11>нет данных — запусти сбор</td></tr>") + SORTJS + "<script>async function deact(id,acc,btn){if(!confirm('Отключить объявление '+id+'? Уйдёт в неактивные, можно вернуть.'))return;btn.disabled=true;btn.textContent='…';try{const r=await fetch('/deactivate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id,account:acc})});const j=await r.json();if(j.ok){btn.textContent='✓ отключено';const tr=btn.closest('tr');if(tr)tr.style.opacity=.4;}else{btn.disabled=false;btn.textContent='🪦 Отключить';alert('Ошибка: '+(j.error||''));}}catch(e){btn.disabled=false;btn.textContent='🪦 Отключить';alert('Сеть: '+e);}}</script>"

@app.get("/stats.csv")
def stats_csv():
    import csv, io
    _, rows = _rows_filtered()
    buf=io.StringIO(); w=csv.writer(buf)
    w.writerow(["Кабинет","Услуга","Город","Объявление","ID","Просмотры","Телефон","Чат"])
    for r in rows:
        w.writerow([r["account"], r.get("service",""), r["city"] or "", r["title"] or "", r["id"],
                    r["advert_views"] or 0, r["phone_views"] or 0, r["threads"] or 0])
    from flask import Response
    return Response("\ufeff"+buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":"attachment;filename=olx_stats.csv"})

CREATE = """<!doctype html><meta charset=utf-8><title>Создать объявление</title>
{theme}
<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:6px"><h2 style="margin:0">➕ Создать объявление <span style="font-size:14px;font-weight:400;color:var(--muted)">&nbsp;<a href="/">🏠 Главная</a> · <a href="/stats">📊 Вчерашняя</a> · <a href="/weekly">📅 Еженедельная</a></span></h2></div>
<p class=muted style="font-size:14px;max-width:760px">Опиши нишу, выбери город и рубрику. Прежде чем создавать — бот покажет, что по этому ТЗ <b>уже есть</b>: в каких кабинетах, сколько штук и с какими показателями. Так избегаем дублей и «солянки».</p>
<div class=card>
<form class=bar method=get style="align-items:flex-end">
<div><div class=muted style="font-size:12px;margin-bottom:4px">Ниша / ключевые слова</div><input name=nisha value="{nisha}" placeholder="напр. москитные сетки" style="min-width:260px"></div>
<div><div class=muted style="font-size:12px;margin-bottom:4px">Город</div><select name=city><option value="">— любой —</option>{cities}</select></div>
<div><div class=muted style="font-size:12px;margin-bottom:4px">Целевая доля, %</div><input name=share value="{share}" type=number min=1 max=100 placeholder="напр. 20" style="width:120px"></div>
<button class=btngreen type=submit>🔍 Показать что уже есть</button>
</form>
</div>
{result}"""

import urllib.parse as _up_mk

_MK_CITY_SLUG = {
    "алматы": "alma-ata", "астана": "astana", "нур-султан": "astana", "шымкент": "shymkent",
    "караганда": "karaganda", "актобе": "aktobe", "тараз": "taraz", "павлодар": "pavlodar",
    "усть-каменогорск": "ust-kamenogorsk", "семей": "semey", "атырау": "atyrau",
    "костанай": "kostanay", "кызылорда": "kyzylorda", "уральск": "uralsk",
    "петропавловск": "petropavlovsk", "актау": "aktau", "туркестан": "turkestan",
    "кокшетау": "kokshetau", "талдыкорган": "taldykorgan", "жезказган": "jezkazgan",
    "темиртау": "temirtau", "экибастуз": "ekibastuz", "рудный": "rudnyy", "балхаш": "balhash",
    "сатпаев": "satpaev", "жанаозен": "janaozen", "риддер": "ridder", "сарань": "saran",
    "аркалык": "arkalyk", "каскелен": "kaskelen",
}
_MK_KIND_TO_CAT = {"услуга": "Услуги", "вакансия": "Работа"}
_MK_FACET_CATS = ("Услуги", "Работа", "Транспорт", "Недвижимость", "Электроника",
                  "Строительство и ремонт", "Дом и сад", "Мода и стиль", "Животные",
                  "Запчасти", "Детский мир", "Хобби, отдых и спорт")


def _mk_q(query):
    s = _re.sub(r"\s+", "-", (query or "").strip())
    return _up_mk.quote(s, safe="-")


def _mk_url(query, slug):
    qq = _mk_q(query)
    return ("https://www.olx.kz/%s/q-%s/" % (slug, qq)) if slug else ("https://www.olx.kz/list/q-%s/" % qq)


def _mk_parse_total(html):
    text = _re.sub(r"<[^>]+>", " ", html)
    m = _re.search(r"Мы нашли\s*(более\s*)?([\d\s ]+?)\s*объявлен", text)
    if m:
        digits = _re.sub(r"[^\d]", "", m.group(2))
        if digits:
            return int(digits), bool(m.group(1))
    m2 = _re.search(r'totalElements\\?["\']?\s*:\s*(\d+)', html)
    if m2:
        return int(m2.group(1)), False
    return None, False


def _mk_parse_facets(html):
    text = _re.sub(r"<[^>]+>", " ", html)
    out = {}
    for cat in _MK_FACET_CATS:
        m = _re.search(_re.escape(cat) + r"\s+(\d[\d\s ]{0,8})", text)
        if m:
            d = _re.sub(r"[^\d]", "", m.group(1))
            if d:
                out[cat] = int(d)
    return out


def _market_counts(query, city=None, kind=None, timeout=8):
    """Сколько ВСЕГО объявлений в публичном поиске OLX по нише (+город,+рубрика).
    Парсит публичную страницу поиска (без токенов). Возвращает dict как раньше."""
    res = {"ok": False, "url": None, "scope": None, "total": None, "total_more": False,
           "kind_count": None, "kind_label": None, "facets": {}, "error": None}
    if not query or not query.strip():
        res["error"] = "пустой запрос"; return res
    if _requests is None:
        res["error"] = "requests недоступен"; return res
    slug = _MK_CITY_SLUG.get((city or "").strip().lower())
    attempts = ([(slug, "город")] if slug else []) + [(None, "страна")]
    last_err = None
    for s, scope in attempts:
        url = _mk_url(query, s)
        try:
            r = _requests.get(url, headers=_PROMO_HEADERS, timeout=timeout)
        except Exception as e:
            last_err = "сеть: %s" % e; continue
        if r.status_code != 200:
            last_err = "HTTP %s" % r.status_code; continue
        total, more = _mk_parse_total(r.text)
        if total is None:
            last_err = "счётчик не найден (анти-бот/JS-рендер)"; continue
        facets = _mk_parse_facets(r.text)
        res.update(ok=True, url=url, scope=scope, total=total, total_more=more, facets=facets)
        if kind == "товар" and facets:
            res["kind_count"] = max(total - facets.get("Услуги", 0) - facets.get("Работа", 0), 0)
            res["kind_label"] = "товары"
        elif kind in _MK_KIND_TO_CAT and _MK_KIND_TO_CAT[kind] in facets:
            res["kind_count"] = facets[_MK_KIND_TO_CAT[kind]]
            res["kind_label"] = _MK_KIND_TO_CAT[kind]
        return res
    res["error"] = last_err or "не удалось получить данные"
    return res


def _market_data(query, city, kind, mine, mine_by_rubric=None, rub_eff=None):
    """Рынок OLX в виде таблицы: Рубрика | в OLX | HUB MASTER | Доля рынка | Создать.
    Возвращает (share_tile, market_table, src). Best-effort."""
    mine_by_rubric = mine_by_rubric or {}
    if not query:
        return "", "", ""
    try:
        m = _market_counts(query, city or None, kind or None)
    except Exception as e:
        m = {"ok": False, "error": str(e)}
    if not m.get("ok"):
        table = ('<div class=card><b>📊 Рынок OLX</b><div class=muted style="font-size:12px;margin-top:6px">'
                 'н/д: %s</div></div>') % (m.get("error") or "")
        return "", table, ""
    total = m["total"]; more = "+" if m.get("total_more") else ""
    scope_lbl = ("г. " + city) if (m.get("scope") == "город" and city) else "по КЗ"
    share = ("%.1f%%" % (mine * 100.0 / total)) if total else "—"
    share_tile = '<div>Доля HUB MASTER (вся ниша)<b style="color:#7aa2ff">%s</b></div>' % share
    try: tgt = float(request.args.get("share") or 0)
    except (TypeError, ValueError): tgt = 0
    try: acc_n = len(runner.accounts())
    except Exception: acc_n = 0
    def _row(name, olx, mn, suffix=""):
        sh = ("%.2f%%" % (mn * 100.0 / olx)) if olx else "—"
        need = "—"
        if tgt > 0 and olx:
            ncreate = max(0, int(round(olx * tgt / 100.0)) - mn)
            if ncreate > 0 and not name.startswith("🌐"):
                need = ("<button onclick=\"mkAds('%s',%d)\" style='min-width:118px;padding:5px 12px;font-size:12px;background:#16604a;border:1px solid #16c79a;color:#7ee3c4;border-radius:7px;cursor:pointer;text-align:center'>🚀 Создать %d</button>"
                        % (name.replace("'","").replace('"',""), ncreate, ncreate))
            else:
                need = "<b style='color:#f5c542;text-shadow:0 0 8px rgba(245,197,66,.55)'>%d</b>" % ncreate
        return ("<tr><td>%s</td><td class=num>%s%s</td><td class=num>%s</td><td class=num>%s</td><td class=num>%s</td></tr>"
                % (name, olx, suffix, (mn or "—"), sh, need))
    body = _row("🌐 Всего на OLX (%s)" % scope_lbl, total, mine, more)
    for c, n in sorted((m.get("facets") or {}).items(), key=lambda kv: -kv[1]):
        body += _row(c, n, mine_by_rubric.get((c or "").strip().lower(), 0))
    tgt_lbl = (" для %.0f%%" % tgt) if tgt > 0 else ""
    cap = (" Безопасный максимум: %d аккаунтов × 3 = %d на нишу." % (acc_n, acc_n * 3)) if acc_n else ""
    table = ('<div class=card><b>📊 Рынок OLX и твоя доля</b>'
             '<table style="margin-top:8px"><thead><tr><th>Рубрика</th><th class=num>в OLX</th>'
             '<th class=num>HUB MASTER</th><th class=num>Доля рынка</th><th class=num>Создать%s</th></tr></thead>'
             '<tbody>%s</tbody></table>'
             '<div class=muted style="font-size:11px;margin-top:6px">«Создать» = цель%% × в OLX − твои текущие в рубрике.%s '
             'Источник: <a href="%s" target="_blank">публичный поиск OLX</a>.</div></div>'
             % (tgt_lbl, body, cap, m["url"]))
    table += ("<script>function mkAds(r,n){if(!confirm('Создать '+n+' объявлений в «'+r+'»? Движок создания ещё собирается.'))return;"
              "alert('Реальное создание подключим следующим шагом: ИИ-генерация контента + фото из существующих. Сначала залей web.py — я считаю схему объявления OLX через /api/raw-advert.');}</script>")
    return "", table, ""


def _create_result(allrows):
    nisha = (request.args.get("nisha","") or "").strip().lower()
    city  = request.args.get("city","")
    kind  = request.args.get("kind","")
    if not (nisha or city or kind):
        return ('<div class=card><span class=muted>Заполни нишу/город/рубрику и нажми '
                '«Показать что уже есть» — увидишь текущую картину по кабинетам.</span></div>')
    words = [w for w in nisha.split() if w]
    def _match(r):
        if city and (r["city"] or "") != city: return False
        if kind and (r["kind"] or "") != kind: return False
        if words:
            hay = ((r["title"] or "")+" "+(r.get("service") or "")).lower()
            if not any(w in hay for w in words): return False
        return True
    matched = [r for r in allrows if _match(r)]
    try:
        witems, _ws, _we = _weekly_data("this")
        wmap = {it["id"]: it for it in witems}
    except Exception:
        wmap = {}
    from collections import Counter
    mine_by_rub = Counter((r.get("rubric") or "").strip().lower() for r in matched if (r.get("rubric") or ""))
    rub_eff = {}
    for r in matched:
        rl = (r.get("rubric") or "").strip().lower()
        if not rl: continue
        it = wmap.get(r["id"])
        rub_eff.setdefault(rl, Counter())[it["vk"] if it else "low"] += 1
    share_tile, market_table, msrc = _market_data((request.args.get("nisha","") or "").strip(), city, kind, len(matched), mine_by_rub, rub_eff)
    if not matched:
        mk = (('<div class=kpi>' + share_tile + '</div>') if share_tile else '') + market_table
        return mk + ('<div class=card style="border-color:#16c79a"><b style="color:#16c79a">Чисто ✓</b><br>'
                '<span class=muted>По этому ТЗ объявлений ещё нет — ниша свободна, дублей не создашь.</span></div>')
    # вердикты эффективности из той же логики, что в недельном отчёте
    BADGE = {"strong":"<b style='color:#16c79a'>🟢 сильное</b>","weak":"<b style='color:#ff5d5d'>🔴 слабое</b>",
             "mid":"<span style='color:#e0b341'>🟡 среднее</span>","low":"<span style='color:#9a9aa3'>⚪ мало данных</span>"}
    cnt = {"strong":0,"weak":0,"mid":0,"low":0}
    agg = {}
    for r in matched:
        it = wmap.get(r["id"]); vk = it["vk"] if it else "low"
        r["_vk"]=vk; r["_leads"]=it["leads"] if it else 0; r["_conv"]=it["conv"] if it else "—"
        cnt[vk]+=1
        rub = (r.get("rubric") or r["kind"] or "—")
        d = agg.setdefault((r["account"], rub), {"n":0,"v":0,"p":0,"t":0,"strong":0,"weak":0,"cities":set()})
        d["n"]+=1; d["v"]+=r["advert_views"] or 0; d["p"]+=r["phone_views"] or 0; d["t"]+=r["threads"] or 0
        if vk=="strong": d["strong"]+=1
        if vk=="weak": d["weak"]+=1
        if r["city"]: d["cities"].add(r["city"])
    items = sorted(agg.items(), key=lambda kv: kv[1]["n"], reverse=True)
    rows_html = ""
    for (acc, rub), d in items:
        rows_html += ("<tr><td>%s</td><td>%s</td><td>%s</td><td class=num>%d</td>"
                      "<td class=num style='color:#16c79a'>%d</td><td class=num style='color:#ff5d5d'>%d</td>"
                      "<td class=num>%d</td><td class=num>%d</td><td class=num>%d</td></tr>") % (
            acc, ", ".join(sorted(d["cities"])) or "—", rub,
            d["n"], d["strong"], d["weak"], d["v"], d["p"], d["t"])
    total_n = sum(d["n"] for _,d in items)
    accts = {}
    for (acc, _rub), d in items:
        accts[acc] = accts.get(acc, 0) + d["n"]
    home = max(accts, key=accts.get) if accts else "—"
    if len(accts) > 1:
        note = ('<div style="margin-top:10px;padding:10px 12px;border:1px solid #e6a233;border-radius:10px;'
                'background:#241d10;color:#f0c674;font-size:13px">⚠️ Эта ниша размазана по <b>%d кабинетам</b> — '
                'риск солянки и дублей. Рекомендую вести её в одном кабинете (%s — там уже больше всего).</div>') % (len(accts), home)
    else:
        note = ('<div style="margin-top:10px;padding:10px 12px;border:1px solid #16c79a;border-radius:10px;'
                'background:#0e1f1a;color:#7ee3c4;font-size:13px">✓ Ниша сосредоточена в одном кабинете (%s) — это правильно. '
                'Новые объявления добавляй сюда же.</div>') % home
    # детальный список объявлений с оценкой (сильные сверху)
    order = {"strong":0,"mid":1,"low":2,"weak":3}
    det = sorted(matched, key=lambda r: (order.get(r["_vk"],9), -(r["_leads"] or 0)))
    det_rows = ""
    for r in det:
        _idc=("<a href='%s' target='_blank' rel='noopener' style='font-family:monospace'>%s ↗</a>"%(r["url"],r["id"])) if r.get("url") else ("<span style='font-family:monospace'>%s</span>"%r["id"])
        det_rows += ("<tr><td>%s</td><td><a href='/advert/%s'>%s</a></td><td class=muted>%s</td><td>%s</td><td>%s</td>"
                     "<td class=num>%s</td><td class=num>%s</td></tr>") % (
            r["account"], r["id"], (r["title"] or "")[:70], _idc, r["city"] or "—",
            BADGE.get(r["_vk"],""), r["_leads"], r["_conv"])
    row2 = market_table or ''
    return ("""<div class=kpi>
<div>Уже есть<b>%d</b></div>
<div>🟢 сильных<b style="color:#16c79a">%d</b></div>
<div>🔴 слабых<b style="color:#ff5d5d">%d</b></div>
<div>🟡 средних<b style="color:#e0b341">%d</b></div>
<div>⚪ мало данных<b style="color:#9a9aa3">%d</b></div>
%s</div>
%s
%s
<p class=muted style="font-size:12px;margin:2px 2px 10px">Оценка за текущую неделю, та же логика что в еженедельном отчёте: 🟢 ≥5 лидов · 🔴 &lt;3 лидов и конверсия &lt;10%% · ⚪ &lt;30 просмотров · 🟡 остальное.</p>
<div class=card><b>По кабинетам</b>
<table style="text-align:center"><thead><tr><th>Кабинет</th><th>Город</th><th>Рубрика</th><th class=num>Всего</th><th class=num>🟢</th><th class=num>🔴</th><th class=num>👁 Просм.</th><th class=num>📞 Тел.</th><th class=num>💬 Чат</th></tr></thead>
<tbody>%s</tbody></table>%s</div>
<div class=card><b>Объявления по эффективности</b>
<table><thead><tr><th>Кабинет</th><th>Объявление</th><th>ID</th><th>Город</th><th>Оценка</th><th class=num>Лиды/нед</th><th class=num>Конв.</th></tr></thead>
<tbody>%s</tbody></table></div>""") % (
        total_n, cnt["strong"], cnt["weak"], cnt["mid"], cnt["low"],
        share_tile, row2, msrc,
        rows_html, note, det_rows)

@app.get("/create")
def create_page():
    allrows, _ = _rows_filtered()
    cities = sorted({r["city"] for r in allrows if r["city"]})
    kind_opts = "".join(
        f'<option value="{k}"{" selected" if k==request.args.get("kind","") else ""}>{lbl}</option>'
        for k,lbl in [("услуга","🛠 Услуга"),("товар","📦 Товар"),("вакансия","💼 Вакансия")])
    return CREATE.format(
        theme=THEME,
        nisha=(request.args.get("nisha","") or "").replace('"',"&quot;"),
        cities=_opts(cities, request.args.get("city","")),
        kinds=kind_opts,
        share=(request.args.get("share","") or "").replace('"',"&quot;"),
        result=_create_result(allrows)) + SORTJS

@app.get("/advert/<int:advert_id>")
def advert_page(advert_id):
    import json
    m = storage.advert_meta(advert_id)
    if not m:
        return "Объявление не найдено", 404
    hist = storage.advert_history(advert_id)
    service = storage.category_names().get(m["category_id"], "")
    cities = storage.city_names()
    try: city = cities.get(int(m["city"])) or (m["city"] or "")
    except (TypeError, ValueError): city = m["city"] or ""
    trows=""; pv=pp=None
    for h in hist:
        dv = (h["advert_views"] or 0)-pv if pv is not None else None
        dp = (h["phone_views"] or 0)-pp if pp is not None else None
        trows += ("<tr><td>%s</td><td class=num>%s</td><td class=num style='color:#16c79a'>%s</td>"
                  "<td class=num>%s</td><td class=num style='color:#16c79a'>%s</td><td class=num>%s</td></tr>") % (
            h["day"], h["advert_views"] or 0, ("+%d"%dv if dv is not None else "—"),
            h["phone_views"] or 0, ("+%d"%dp if dp is not None else "—"), h["threads"] or 0)
        pv=h["advert_views"] or 0; pp=h["phone_views"] or 0
    data = json.dumps({"labels":[h["day"] for h in hist],
                       "views":[h["advert_views"] or 0 for h in hist],
                       "phones":[h["phone_views"] or 0 for h in hist]}, ensure_ascii=False)
    title = (m["title"] or "").replace("<","&lt;")
    return (
      "<!doctype html><meta charset=utf-8><title>Динамика</title>"
      "<script src='https://cdn.jsdelivr.net/npm/chart.js'></script>"
      + THEME +
      "<div class=wrap>"
      "<h2>"+title+"</h2>"
      "<div class=meta>Кабинет: "+str(m['account'])+" · Услуга: "+str(service)+" · Город: "+str(city)+"</div>"
      "<a href='/stats'>← к статистике</a>"
      "<canvas id=c height=110></canvas>"
      "<table><thead><tr><th>Дата</th><th class=num>👁 всего</th><th class=num>+за день</th>"
      "<th class=num>📞 всего</th><th class=num>+за день</th><th class=num>💬 чат</th></tr></thead>"
      "<tbody>"+(trows or "<tr><td colspan=6>пока один срез — динамика появится со 2-го дня</td></tr>")+"</tbody></table>"
      "</div>"
      "<script>const d="+data+";new Chart(document.getElementById('c'),{type:'line',"
      "data:{labels:d.labels,datasets:["
      "{label:'Просмотры',data:d.views,borderColor:'#16c79a',tension:.3},"
      "{label:'Звонки',data:d.phones,borderColor:'#ff5d5d',tension:.3}]},"
      "options:{plugins:{legend:{labels:{color:'#e6edf3'}}},scales:{x:{ticks:{color:'#9aa7b2'}},y:{ticks:{color:'#9aa7b2'}}}}});</script>")

def _weekly_data(week):
    import datetime, os as _os
    today=datetime.date.today(); mon=today-datetime.timedelta(days=today.weekday())
    if week=="prev": start=mon-datetime.timedelta(days=7); end=mon-datetime.timedelta(days=1)
    else: start=mon; end=today
    rows=storage.weekly_rows(start.isoformat(), end.isoformat())
    cats=_resolve_categories({r["category_id"] for r in rows}); kinds=storage.category_kinds()
    def _cid(v):
        try: return int(v)
        except (TypeError, ValueError): return v
    cities=_resolve_cities({c for c in (_cid(r["city"]) for r in rows) if isinstance(c,int)})
    CONV=float(_os.getenv("WEAK_CONV_PCT","10")); MINV=int(_os.getenv("WEEK_MIN_VIEWS","30"))
    STRONG=int(_os.getenv("WEEK_STRONG_LEADS","5")); WEAK=int(_os.getenv("WEEK_WEAK_LEADS","3"))
    def days_live(r):
        ss=r.get("activated_at") or r.get("created_at")
        try: return (today-datetime.date.fromisoformat(ss[:10])).days
        except Exception: return None
    items=[]
    for r in rows:
        dv=(r["e_v"] or 0)-(r["s_v"] or 0); dp=(r["e_p"] or 0)-(r["s_p"] or 0); dt=(r["e_t"] or 0)-(r["s_t"] or 0)
        leads=dp+dt; conv=(dp/dv*100) if dv>0 else None
        if dv<MINV: vk="low"
        elif leads>=STRONG: vk="strong"
        elif leads<WEAK and (conv is None or conv<CONV): vk="weak"
        else: vk="mid"
        cid=_cid(r["city"]); city=cities.get(cid,"") if isinstance(cid,int) else (cid or "")
        tu=r.get("top_until"); top=(tu[:10]) if (tu and tu[:10]>=today.isoformat()) else ""
        _dl=days_live(r); _dead=(dv<14 and dp<=5)  # оценка по недельному отчёту, без учёта дней в работе
        items.append({"account":r["account"],"service":cats.get(r["category_id"],""),"city":city,"vk":vk,
            "kind":kinds.get(r["category_id"]) or "","id":r["id"],"url":r.get("url") or "","title":(r["title"] or "")[:70],
            "dl":_dl,"dv":dv,"leads":leads,"dp":dp,"dead":_dead,
            "conv":("%.0f%%"%conv) if conv is not None else "—","top":top,
            "thr":(CONV,MINV,STRONG,WEAK)})
    return items, start, end

def _weekly_filtered(items):
    fc=request.args.get("city",""); fa=request.args.get("account",""); fs=request.args.get("service",""); fv=request.args.get("verdict",""); fk=request.args.get("kind","")
    def _vok(it):
        if not fv: return True
        if fv=="dead": return bool(it.get("dead"))
        return it["vk"]==fv
    return [it for it in items if (not fc or it["city"]==fc) and (not fa or it["account"]==fa)
            and (not fs or it["service"]==fs) and _vok(it) and (not fk or it["kind"]==fk)]

VLBL={"strong":"🟢 В ТОП","weak":"🔴 На замену","mid":"🟡 Средне","low":"⚪ Мало данных"}

@app.get("/weekly.csv")
def weekly_csv():
    import csv, io
    from flask import Response
    items,start,end=_weekly_data(request.args.get("week","this")); sel=_weekly_filtered(items)
    REC={"strong":"в ТОП","weak":"заменить","mid":"наблюдать","low":"-"}
    buf=io.StringIO(); w=csv.writer(buf)
    w.writerow(["Кабинет","Услуга","Город","Объявление","ID","В работе (дн)","Просмотры/нед","Лиды","Звонки","Конверсия","Оценка","ТОП до","Рекомендация"])
    for it in sel:
        w.writerow([it["account"],it["service"],it["city"],it["title"],it["id"],it["dl"] or "",it["dv"],it["leads"],it["dp"],it["conv"],
                    VLBL[it["vk"]].split(" ",1)[1], it["top"], REC[it["vk"]]])
    return Response("﻿"+buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition":"attachment;filename=olx_weekly.csv"})

@app.get("/weekly")
def weekly_page():
    import urllib.parse as _up, json
    week=request.args.get("week","this")
    items,start,end=_weekly_data(week); sel=_weekly_filtered(items)
    dead_list=[{"id":it["id"],"account":it["account"]} for it in sel if it.get("dead")]
    CONV,MINV,STRONG,WEAK = items[0]["thr"] if items else (10,30,5,3)
    BADGE={"strong":"<b style='color:#16c79a'>🟢 хорошо</b>","weak":"<b style='color:#ff5d5d'>🔴 слабо</b>",
           "mid":"<span style='color:#e0b341'>🟡 средне</span>","low":"<span style='color:#9a9aa3'>⚪ мало данных</span>"}
    REC={"strong":"🔝 в ТОП","weak":"⛔ заменить","mid":"наблюдать","low":"—"}
    cnt=lambda k: sum(1 for it in sel if it["vk"]==k)
    strong,weak,mid,low=cnt("strong"),cnt("weak"),cnt("mid"),cnt("low")
    body=""
    for it in sel:
        topcell=("🔝 до "+it["top"]) if it["top"] else "—"
        idcell=("<a href='%s' target='_blank' rel='noopener' style='font-family:monospace'>%s ↗</a>"%(it["url"],it["id"])) if it["url"] else ("<span style='font-family:monospace'>%s</span>"%it["id"])
        reccell=("<button onclick=\"deact(%s,'%s',this)\" title='Деактивировать в OLX (обратимо)' style='padding:4px 9px;font-size:12px;background:#3a1414;border:1px solid #5a1f1f;color:#ff9d9d;border-radius:7px;cursor:pointer'>🪦 Отключить</button>"%(it["id"],it["account"])) if it.get("dead") else REC[it["vk"]]
        body+=("<tr><td>%s</td><td>%s</td><td>%s</td><td><a href='/advert/%s'>%s</a></td>"
               "<td class=muted>%s</td>"
               "<td class=num>%s</td><td class=num>%s</td><td class=num><b>%s</b></td><td class=num>%s</td><td class=num>%s</td>"
               "<td>%s</td><td>%s</td><td>%s</td></tr>") % (
            it["account"], it["service"], it["city"] or "—", it["id"], it["title"], idcell,
            ("%d дн."%it["dl"] if it["dl"] is not None else "—"), it["dv"], it["leads"], it["dp"], it["conv"],
            BADGE[it["vk"]], topcell, reccell)
    def opts(vals, selv):
        return "".join("<option value=\"%s\"%s>%s</option>"%(v,(" selected" if v==selv else ""),v) for v in vals)
    cities_l=sorted({it["city"] for it in items if it["city"]}); accs_l=sorted({it["account"] for it in items}); svcs_l=sorted({it["service"] for it in items if it["service"]})
    f_city=request.args.get("city",""); f_acc=request.args.get("account",""); f_svc=request.args.get("service",""); f_v=request.args.get("verdict",""); f_k=request.args.get("kind","")
    vmap=[("","Любая оценка"),("strong","🟢 В ТОП"),("weak","🔴 На замену"),("mid","🟡 Средне"),("low","⚪ Мало данных"),("dead","🪦 Мёртвые")]
    vopts="".join("<option value=\"%s\"%s>%s</option>"%(k,(" selected" if k==f_v else ""),lbl) for k,lbl in vmap)
    kmap=[("","Все рубрики"),("услуга","🛠 Услуга"),("товар","📦 Товар"),("вакансия","💼 Вакансия")]
    kopts="".join("<option value=\"%s\"%s>%s</option>"%(k,(" selected" if k==f_k else ""),lbl) for k,lbl in kmap)
    other="prev" if week=="this" else "this"; other_lbl="← прошлая неделя" if week=="this" else "эта неделя →"
    keep={k:v for k,v in request.args.items() if k!="week"}; other_qs="&"+_up.urlencode(keep) if keep else ""
    csv_qs="?"+_up.urlencode({k:v for k,v in request.args.items()}) if request.args else ""
    rule=("🟢 ≥%d лидов · 🔴 &lt;%d лидов и конв.&lt;%.0f%% · ⚪ &lt;%d просм. · 🟡 остальное"%(STRONG,WEAK,CONV,MINV))
    return (THEME +
      "<title>Еженедельная статистика</title>"
      "<div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:6px'>"
      "<div class='nav-links'>    <a href='/'>Главная</a>    <a href='/stats'>Вчерашняя</a>    <a href='/weekly' class='active'>Еженедельная</a>    <a href='/dashboard'>Дашборд</a>    <a href='/bots'>Боты</a>    <a href='/whatsapp'>WhatsApp бот</a>    <a href='/logs'>Логи</a></div><h2 style='margin:0'>Еженедельная статистика</h2>"
      "<a href='/weekly.csv"+csv_qs+"'><button type=button>⬇ Скачать CSV</button></a></div>"
      "<div class=muted>Период: <b style='color:#fff'>"+start.isoformat()+" — "+end.isoformat()+"</b> &nbsp; <a href='/weekly?week="+other+other_qs+"'>"+other_lbl+"</a></div>"
      "<div class=rule>Правило оценки: "+rule+"</div>"
      "<form class=bar method=get>"
      "<input type=hidden name=week value=\""+week+"\">"
      "<select name=verdict onchange='this.form.submit()'>"+vopts+"</select>"
      "<select name=city onchange='this.form.submit()'><option value=''>Все города</option>"+opts(cities_l,f_city)+"</select>"
      "<select name=account onchange='this.form.submit()'><option value=''>Все кабинеты</option>"+opts(accs_l,f_acc)+"</select>"
      "<select name=service onchange='this.form.submit()'><option value=''>Все услуги</option>"+opts(svcs_l,f_svc)+"</select>"
      "</form>"
      "<div class=kpi>"
      "<div>Объявлений<b>"+str(len(sel))+"</b></div>"
      "<div>🟢 В ТОП<b style='color:#16c79a'>"+str(strong)+"</b></div>"
      "<div>🔴 На замену<b style='color:#ff5d5d'>"+str(weak)+"</b></div>"
      "<div>🟡 Средне<b style='color:#e0b341'>"+str(mid)+"</b></div>"
      "<div>⚪ Мало данных<b style='color:#9a9aa3'>"+str(low)+"</b></div>"
      "<div>🪦 Мёртвые<b style='color:#ff9d9d'>"+str(len(dead_list))+"</b></div></div>"
      + (("<div style='margin:8px 0 12px'><button onclick='deactAll()' style='padding:8px 16px;background:#3a1414;border:1px solid #6a2020;color:#ff9d9d;border-radius:9px;cursor:pointer;font-weight:700'>🪦 Отключить все мёртвые ("+str(len(dead_list))+")</button> <span class=muted style='font-size:13px'>— уйдут в неактивные в OLX, можно вернуть командой activate</span></div>") if dead_list else "") +
      "<table><thead><tr><th>Кабинет</th><th>Услуга</th><th>Город</th><th>Объявление</th><th>ID</th>"
      "<th>В работе</th><th class=num>👁 за нед</th><th class=num>Лиды</th><th class=num>📞</th><th class=num>Конв.</th>"
      "<th>Оценка</th><th>ТОП</th><th>Рекомендация</th></tr></thead>"
      "<tbody>"+(body or "<tr><td colspan=13>нет объявлений под фильтр</td></tr>")+"</tbody></table>" + SORTJS +
      "<script>window.__dead="+json.dumps(dead_list, ensure_ascii=False)+";"
      "async function deact(id,acc,btn){if(!confirm('Отключить объявление '+id+'? Уйдёт в неактивные, можно вернуть.'))return;btn.disabled=true;btn.textContent='…';try{const r=await fetch('/deactivate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id,account:acc})});const j=await r.json();if(j.ok){btn.textContent='✓ отключено';const tr=btn.closest('tr');if(tr)tr.style.opacity=.4;}else{btn.disabled=false;btn.textContent='🪦 Отключить';alert('Ошибка: '+(j.error||''));}}catch(e){btn.disabled=false;btn.textContent='🪦 Отключить';alert('Сеть: '+e);}}"
      "async function deactAll(){const d=window.__dead||[];if(!d.length)return;if(!confirm('Отключить все мёртвые ('+d.length+')? Уйдут в неактивные, можно вернуть.'))return;for(const x of d){try{await fetch('/deactivate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(x)});}catch(e){}}location.reload();}"
      "</script>")

@app.post("/deactivate")
def deactivate_advert():
    data = request.get_json(silent=True) or {}
    advert_id = data.get("id"); account = data.get("account")
    if not advert_id or not account:
        return jsonify(ok=False, error="нет id или account"), 400
    try:
        OlxClient(str(account)).command(int(advert_id), "deactivate", is_success=False)
        storage.set_advert_status(int(advert_id), "inactive")
        return jsonify(ok=True)
    except Exception as e:
        detail = ""
        resp = getattr(e, "response", None)
        if resp is not None:
            try: detail = " | OLX: " + str(resp.json())
            except Exception: detail = " | OLX: " + (resp.text or "")[:300]
        return jsonify(ok=False, error=str(e)+detail), 500


def _comp_init():
    c = storage.conn()
    c.execute("CREATE TABLE IF NOT EXISTS competitors(name TEXT, offer_id TEXT, PRIMARY KEY(name, offer_id))")
    c.execute("CREATE TABLE IF NOT EXISTS competitor_meta(name TEXT PRIMARY KEY, query TEXT)")
    c.commit(); c.close()


def _comp_query(name):
    _comp_init()
    c = storage.conn()
    row = c.execute("SELECT query FROM competitor_meta WHERE name=?", (name,)).fetchone()
    c.close()
    return (row["query"] if row else "") or ""


def _comp_set_query(name, query):
    _comp_init()
    c = storage.conn()
    c.execute("INSERT INTO competitor_meta(name, query) VALUES(?,?) "
              "ON CONFLICT(name) DO UPDATE SET query=excluded.query", (name, query or ""))
    c.commit(); c.close()


def _comp_list():
    _comp_init()
    c = storage.conn()
    rows = c.execute("SELECT name, offer_id FROM competitors ORDER BY rowid").fetchall()
    c.close()
    out = {}
    for r in rows:
        out.setdefault(r["name"], []).append(r["offer_id"])
    return out


def _comp_add(name, ids):
    _comp_init()
    c = storage.conn()
    for i in ids:
        c.execute("INSERT OR IGNORE INTO competitors(name, offer_id) VALUES(?,?)", (name, str(i)))
    c.commit(); c.close()


def _comp_del(name):
    _comp_init()
    c = storage.conn()
    c.execute("DELETE FROM competitors WHERE name=?", (name,))
    c.execute("DELETE FROM competitor_meta WHERE name=?", (name,))
    c.commit(); c.close()


def _comp_rename(old, new):
    if not old or not new or old == new:
        return
    _comp_init()
    c = storage.conn()
    # объявления: перенести на новую метку (дубли-конфликты по PK пропустит IGNORE)
    c.execute("UPDATE OR IGNORE competitors SET name=? WHERE name=?", (new, old))
    c.execute("DELETE FROM competitors WHERE name=?", (old,))
    # ключ поиска: перенести, если у новой метки его ещё нет
    c.execute("INSERT OR IGNORE INTO competitor_meta(name, query) "
              "SELECT ?, query FROM competitor_meta WHERE name=?", (new, old))
    c.execute("DELETE FROM competitor_meta WHERE name=?", (old,))
    c.commit(); c.close()


def _comp_default_query(name, query):
    """Проставить дефолтный ключ ТОЛЬКО если его ещё ни разу не задавали
    (INSERT OR IGNORE — если строка есть, даже с пустым ключом, не трогаем)."""
    _comp_init()
    c = storage.conn()
    c.execute("INSERT OR IGNORE INTO competitor_meta(name, query) VALUES(?,?)", (name, query or ""))
    c.commit(); c.close()


def _comp_groups():
    """Сохранённые конкуренты из БД; при пустой таблице — посев из COMPETITORS."""
    g = _comp_list()
    if not g:
        for n, ids in COMPETITORS.items():
            _comp_add(n, ids)
        g = _comp_list()
    # бэкфилл дефолтных ключей (не перезатирает уже заданные/очищенные)
    for n, q in COMPETITOR_QUERY.items():
        if n in g:
            _comp_default_query(n, q)
    return g


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _promo_badges(o):
    b = []
    if o.get("top"):         b.append("<span style='background:#f5c542;color:#1a1505;padding:2px 8px;border-radius:6px;font-weight:700;font-size:12px'>ТОП</span>")
    if o.get("premium"):     b.append("<span style='background:#7c4dff;color:#fff;padding:2px 8px;border-radius:6px;font-weight:700;font-size:12px'>Премиум</span>")
    if o.get("highlighted"): b.append("<span style='background:#16c79a;color:#04130d;padding:2px 8px;border-radius:6px;font-weight:700;font-size:12px'>Выделено</span>")
    if o.get("urgent"):      b.append("<span style='background:#e63333;color:#fff;padding:2px 8px;border-radius:6px;font-weight:700;font-size:12px'>Срочно</span>")
    return " ".join(b) if b else "<span class=muted>обычное</span>"


@app.get("/promo")
def promo_page():
    groups = _comp_groups()

    blocks = []
    for name, ids in groups.items():
        gq = _comp_query(name)
        offers = [fetch_offer(i) for i in ids]
        promoted = sum(1 for o in offers if o.get("ok") and (o.get("top") or o.get("highlighted") or o.get("urgent") or o.get("premium")))
        entries = []   # (sort_cat, sort_rank, html) — для сортировки по рубрике, затем по месту
        err_rows = []
        for o in offers:
            idlink = ("<a href='%s' target='_blank' rel='noopener' style='font-family:monospace'>%s ↗</a>" % (o["url"], o["id"])) if o.get("url") else ("<span style='font-family:monospace'>%s</span>" % o["id"])
            if not o.get("ok"):
                err_rows.append("<tr><td>%s</td><td colspan=8 class=muted>⚠ %s</td></tr>" % (idlink, o.get("error") or "нет данных"))
                continue
            title = (o["title"] or "—")[:60]
            dsr = o.get("days_since_refresh")
            if dsr is None:
                refresh = o.get("refreshed") or "—"
            elif dsr <= 0:
                refresh = "<b style='color:#16c79a'>сегодня</b>"
            elif dsr == 1:
                refresh = "<b style='color:#16c79a'>вчера</b>"
            else:
                col = "#16c79a" if dsr <= 3 else ("#f5c542" if dsr <= 10 else "var(--muted)")
                refresh = "<span style='color:%s'>%d дн. назад</span>" % (col, dsr)
            pos = fetch_position(o, query=gq or None)
            suffix = "" if gq else " <span class=muted style='font-size:11px'>(вся рубрика)</span>"
            if pos.get("self_promoted"):
                poscell = "<span style='color:#f5c542'>в платном ТОПе</span>"; sort_rank = 0
            elif pos.get("found") and pos.get("organic_rank"):
                rank = pos["organic_rank"]; pg = pos.get("page") or 1
                pc = "#16c79a" if rank <= 10 else ("#f5c542" if rank <= 30 else "var(--text)")
                poscell = "<b style='color:%s'>%d место</b> <span class=muted>· стр.%d</span>%s" % (pc, rank, pg, suffix)
                sort_rank = rank
            elif pos.get("error"):
                poscell = "<span class=muted>н/д</span>"; sort_rank = 10 ** 6
            else:
                poscell = "<span class=muted>ниже %d</span>" % (pos.get("total_scanned") or 0); sort_rank = 10 ** 6
            html = ("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                    idlink, title, o.get("seller") or "—", _esc(o.get("category_name") or "—"),
                    o.get("city") or "—", o.get("price") or "—", _promo_badges(o), refresh, poscell))
            entries.append(((o.get("category_name") or "￿"), sort_rank, html))
        # сортируем: сначала по рубрике (вместе), внутри рубрики — по месту 1→вниз
        entries.sort(key=lambda e: (e[0], e[1]))
        rows = [e[2] for e in entries] + err_rows
        table = ("<table><thead><tr><th>ID</th><th>Заголовок</th><th>Продавец</th>"
                 "<th>Категория</th><th>Город</th><th>Цена</th><th>Продвижение</th><th>Последнее поднятие</th>"
                 "<th>Позиция (без ТОПов)</th></tr></thead>"
                 "<tbody>" + "".join(rows) + "</tbody></table>")
        delbtn = ("<form method=post action=/promo/del style='display:inline' "
                  "onsubmit=\"return confirm('Убрать конкурента «%s» из наблюдения?')\">"
                  "<input type=hidden name=name value=\"%s\">"
                  "<button style='padding:4px 12px;font-size:12px;background:#3a1414;border-color:#6a2020;color:#ff9d9d'>🗑 Удалить</button></form>"
                  % (_esc(name), _esc(name)))
        keyform = ("<form method=post action=/promo/key style='display:inline-flex;gap:6px;align-items:center'>"
                   "<input type=hidden name=name value=\"%s\">"
                   "<span class=muted style='font-size:12px'>ключ:</span>"
                   "<input name=query value=\"%s\" placeholder='вся рубрика' style='padding:4px 8px;font-size:12px;min-width:150px'>"
                   "<button style='padding:4px 10px;font-size:12px'>↻</button></form>"
                   % (_esc(name), _esc(gq)))
        head = ("<div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px'>"
                "<h3 style='margin:0'>🎯 %s</h3>"
                "<span style='display:flex;align-items:center;gap:12px;flex-wrap:wrap'>"
                "%s<span class=muted>объявлений: %d · продвигаются: <b style='color:#f5c542'>%d</b></span>%s</span></div>"
                % (_esc(name), keyform, len(ids), promoted, delbtn))
        ctrls = ("<div style='display:flex;gap:10px;flex-wrap:wrap;margin:10px 0 4px'>"
                 "<form method=post action=/promo/rename style='display:inline-flex;gap:6px;align-items:center'>"
                 "<input type=hidden name=old value=\"%s\">"
                 "<input name=new value=\"%s\" required style='padding:5px 9px;font-size:13px;min-width:170px'>"
                 "<button style='padding:5px 12px;font-size:13px'>✎ Переименовать</button></form>"
                 "<form method=post action=/promo/addids style='display:inline-flex;gap:6px;align-items:center;flex:1;min-width:260px'>"
                 "<input type=hidden name=name value=\"%s\">"
                 "<input name=ids placeholder='ещё ID через запятую' required style='padding:5px 9px;font-size:13px;flex:1'>"
                 "<button class=btngreen style='padding:5px 12px;font-size:13px'>＋ Добавить ID</button></form>"
                 "</div>" % (_esc(name), _esc(name), _esc(name)))
        blocks.append("<div class=card>" + head + ctrls + table + "</div>")

    body = "".join(blocks) if blocks else "<div class=card class=muted>Нет конкурентов под наблюдением.</div>"
    addform = ("<div class=card><b>Добавить конкурента</b>"
               "<p class=muted style='font-size:13px;margin:6px 0'>Метка + ID объявлений через запятую + ключ поиска "
               "(по нему считается место в выдаче; без ключа — место по всей рубрике). Удалить можно кнопкой 🗑 у его таблицы.</p>"
               "<form method=post action=/promo/add style='display:flex;gap:8px;flex-wrap:wrap'>"
               "<input name=name placeholder='метка конкурента' required style='min-width:180px'>"
               "<input name=ids placeholder='397610224, 397610305, ...' required style='flex:1;min-width:240px'>"
               "<input name=query placeholder='ключ: москитные сетки' style='min-width:200px'>"
               "<button class=btngreen>＋ Добавить</button></form></div>")
    return (THEME +
            "<title>Продвижение конкурентов</title>"
            "<div style='display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:6px'>"
            "<h2 style='margin:0'>🚀 Продвижение конкурентов "
            "<span style='font-size:14px;font-weight:400;color:var(--muted)'>&nbsp;"
            "<a href='/'>🏠 Главная</a> · <a href='/stats'>📊 Вчерашняя</a> · <a href='/weekly'>📅 Еженедельная</a></span></h2></div>"
            "<p class=muted style='font-size:13px;max-width:820px'>Видно платное продвижение конкурента (ТОП / Премиум / Выделено / Срочно) "
            "и как часто он поднимает объявления. <b>Позиция (без ТОПов)</b> — органическое место в выдаче рубрики (категория+город): из счёта исключены ровно те карточки, "
            "что OLX пометил платными ТОП-слотами (metadata.promoted), а не все владельцы пакета. <b>Категория</b> — конечная рубрика объявления. "
            "Данные кэшируются 15 мин. Просмотры и звонки по чужим объявлениям OLX не отдаёт — это приватные данные.</p>"
            + body + addform)


@app.post("/promo/add")
def promo_add():
    name = (request.form.get("name") or "").strip()
    raw = (request.form.get("ids") or "").replace(" ", "")
    query = (request.form.get("query") or "").strip()
    ids = [x for x in raw.replace(";", ",").split(",") if x.strip()]
    if name and ids:
        _comp_add(name, ids)
        if query:
            _comp_set_query(name, query)
    return redirect("/promo")


@app.post("/promo/key")
def promo_key():
    name = (request.form.get("name") or "").strip()
    query = (request.form.get("query") or "").strip()
    if name:
        _comp_set_query(name, query)
    return redirect("/promo")


@app.post("/promo/rename")
def promo_rename():
    old = (request.form.get("old") or "").strip()
    new = (request.form.get("new") or "").strip()
    if old and new:
        _comp_rename(old, new)
    return redirect("/promo")


@app.post("/promo/addids")
def promo_addids():
    name = (request.form.get("name") or "").strip()
    raw = (request.form.get("ids") or "").replace(" ", "")
    ids = [x for x in raw.replace(";", ",").split(",") if x.strip()]
    if name and ids:
        _comp_add(name, ids)
    return redirect("/promo")


@app.post("/promo/del")
def promo_del():
    name = (request.form.get("name") or "").strip()
    if name:
        _comp_del(name)
    return redirect("/promo")

@app.get("/correct")
def correct_page():
    import json, urllib.parse as _up
    week=request.args.get("week","prev")
    items, start, end = _weekly_data(week)
    fc=request.args.get("city",""); fa=request.args.get("account","")
    other="this" if week=="prev" else "prev"; other_lbl="эта неделя →" if week=="prev" else "← прошлая неделя"
    keep={k:v for k,v in request.args.items() if k!="week"}; other_qs=("&"+_up.urlencode(keep)) if keep else ""
    dead=[it for it in items if it.get("dead") and (not fc or it["city"]==fc) and (not fa or it["account"]==fa)]
    dead_list=[{"id":it["id"],"account":it["account"]} for it in dead]
    body=""
    for it in dead:
        idcell=("<a href='%s' target='_blank' rel='noopener' style='font-family:monospace'>%s ↗</a>"%(it["url"],it["id"])) if it["url"] else ("<span style='font-family:monospace'>%s</span>"%it["id"])
        body+=("<tr><td>%s</td><td>%s</td><td>%s</td><td><a href='/advert/%s'>%s</a></td><td class=muted>%s</td>"
               "<td class=num>%s</td><td class=num>%s</td><td class=num>%s</td><td class=num>%s</td>"
               "<td><button onclick=\"deact(%s,'%s',this)\" style='padding:5px 11px;font-size:13px;background:#3a1414;border:1px solid #5a1f1f;color:#ff9d9d;border-radius:8px;cursor:pointer'>🪦 Отключить</button></td></tr>") % (
            it["account"], it["service"], it["city"] or "—", it["id"], it["title"], idcell,
            ("%d дн."%it["dl"] if it["dl"] is not None else "—"), it["dv"], it["leads"], it["dp"],
            it["id"], it["account"])
    def opts(vals,selv): return "".join("<option value=\"%s\"%s>%s</option>"%(v,(" selected" if v==selv else ""),v) for v in vals)
    cities_l=sorted({it["city"] for it in items if it.get("dead") and it["city"]})
    accs_l=sorted({it["account"] for it in items if it.get("dead")})
    bulk = (("<button onclick='deactAll()' style='padding:9px 18px;background:#3a1414;border:1px solid #6a2020;color:#ff9d9d;border-radius:9px;cursor:pointer;font-weight:700'>🪦 Отключить все мёртвые ("+str(len(dead_list))+")</button>") if dead_list else "<span class=muted>Мёртвых объявлений нет 👍</span>")
    js=("<script>window.__dead="+json.dumps(dead_list,ensure_ascii=False)+";"
        "async function deact(id,acc,btn){if(!confirm('Отключить объявление '+id+'? Уйдёт в неактивные, можно вернуть.'))return;btn.disabled=true;btn.textContent='…';try{const r=await fetch('/deactivate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:id,account:acc})});const j=await r.json();if(j.ok){btn.textContent='✓ отключено';const tr=btn.closest('tr');if(tr)tr.style.opacity=.4;}else{btn.disabled=false;btn.textContent='🪦 Отключить';alert('Ошибка: '+(j.error||''));}}catch(e){btn.disabled=false;btn.textContent='🪦 Отключить';alert('Сеть: '+e);}}"
        "async function deactAll(){const d=window.__dead||[];if(!d.length)return;if(!confirm('Отключить все мёртвые ('+d.length+')? Уйдут в неактивные, можно вернуть.'))return;for(const x of d){try{await fetch('/deactivate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(x)});}catch(e){}}location.reload();}"
        "</script>")
    return (THEME +
      "<title>Корректировка объявлений</title>"
      "<h2 style='margin:0 0 4px'>🛠 Корректировка объявлений <span style='font-size:14px;font-weight:400;color:var(--muted)'>&nbsp;<a href='/'>🏠 Главная</a> · <a href='/weekly'>📅 Еженедельная</a></span></h2>"
      "<div class=muted style='margin-bottom:6px'>Оценка по недельному отчёту (пн 00:00 – вс 23:55). Мёртвое: за неделю &lt;14 просмотров (&lt;2/день) и ≤5 звонков. Если звонков &gt;5 — рабочее. Отключение убирает из выдачи OLX (обратимо).</div>"
      "<div class=muted style='margin-bottom:10px'>Период: <b style='color:#fff'>"+start.isoformat()+" — "+end.isoformat()+"</b> &nbsp; <a href='/correct?week="+other+other_qs+"'>"+other_lbl+"</a></div>"
      "<form class=bar method=get>"
      "<input type=hidden name=week value=\""+week+"\">"
      "<select name=city onchange='this.form.submit()'><option value=''>Все города</option>"+opts(cities_l,fc)+"</select>"
      "<select name=account onchange='this.form.submit()'><option value=''>Все кабинеты</option>"+opts(accs_l,fa)+"</select>"
      "</form>"
      "<div class=kpi><div>🪦 Мёртвых<b style='color:#ff9d9d'>"+str(len(dead_list))+"</b></div></div>"
      "<div style='margin:8px 0 12px'>"+bulk+"</div>"
      "<table><thead><tr><th>Кабинет</th><th>Услуга</th><th>Город</th><th>Объявление</th><th>ID</th>"
      "<th>В работе</th><th class=num>👁 за нед</th><th class=num>Лиды</th><th class=num>📞</th><th>Действие</th></tr></thead>"
      "<tbody>"+(body or "<tr><td colspan=10>мёртвых объявлений нет 👍</td></tr>")+"</tbody></table>" + SORTJS + js)

@app.get("/api/raw-advert")
def raw_advert():
    """Диагностика: полная структура существующего объявления (для клонирования при создании)."""
    acc = request.args.get("acc"); aid = request.args.get("id")
    if not acc or not aid:
        return jsonify(error="нужны параметры acc и id"), 400
    try:
        return jsonify(OlxClient(acc).advert(int(aid)))
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.get("/api/cat-attrs")
def cat_attrs():
    """Диагностика: обязательные/опциональные атрибуты категории."""
    acc = request.args.get("acc"); cat = request.args.get("cat")
    if not acc or not cat:
        return jsonify(error="нужны параметры acc и cat"), 400
    try:
        return jsonify(OlxClient(acc)._req("GET", f"/categories/{cat}/attributes"))
    except Exception as e:
        return jsonify(error=str(e)), 500


DASHBOARD_HTML = """<!doctype html>
<meta charset="utf-8">
<title>Аналитическая Панель</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #0b0c10; --card: #15161c; --card-hover: #1c1d25;
  --text: #ffffff; --muted: #8b8b99;
  --accent: #16c79a; --accent-bg: rgba(22, 199, 154, 0.1);
  --border: #23242f; --danger: #ff5d5d; --blue: #3a86ff;
}
body { margin: 0; padding: 24px; background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; }
h1, h2, h3, h4 { font-family: 'Montserrat', sans-serif; text-transform: uppercase; margin: 0; }
a { color: var(--text); text-decoration: none; }
.header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 24px; }
.title-area h1 { font-size: 28px; font-weight: 800; letter-spacing: 0.5px; }
.title-area .subtitle { color: var(--muted); font-size: 13px; margin-top: 6px; font-weight: 500; }
.nav-pills { display: flex; gap: 8px; }
.nav-pills a { padding: 8px 16px; border-radius: 6px; font-size: 11px; font-weight: 700; border: 1px solid var(--border); color: var(--muted); text-transform: uppercase; transition: 0.2s; }
.nav-pills a:hover { border-color: var(--muted); }
.nav-pills a.active { background: var(--accent); color: #000; border-color: var(--accent); }
.grid-4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 16px; }
.card { background: var(--card); border-radius: 12px; padding: 20px; border: 1px solid var(--border); box-shadow: 0 10px 30px rgba(0,0,0,0.2); }
.kpi-head { display: flex; justify-content: space-between; align-items: center; font-size: 11px; font-weight: 700; color: var(--muted); text-transform: uppercase; margin-bottom: 16px; }
.kpi-icon { width: 24px; height: 24px; border-radius: 6px; background: var(--accent-bg); color: var(--accent); display: flex; align-items: center; justify-content: center; font-size: 12px; }
.kpi-val { font-size: 32px; font-weight: 700; font-family: 'Montserrat', sans-serif; margin-bottom: 8px; }
.kpi-trend { font-size: 12px; font-weight: 600; }
.kpi-trend.up { color: var(--accent); }
.kpi-trend.down { color: var(--danger); }
.grid-2 { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; margin-bottom: 16px; }
@media(max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }
.chart-wrap { height: 260px; width: 100%; margin-top: 16px; }
.ch-row { display: flex; justify-content: space-between; align-items: center; margin-top: 20px; font-size: 12px; font-weight: 600; }
.bar-bg { width: 100%; height: 6px; background: var(--border); border-radius: 3px; margin-top: 8px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 3px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 12px; }
th, td { padding: 12px 10px; border-bottom: 1px solid var(--border); text-align: left; }
th { color: var(--muted); font-weight: 700; text-transform: uppercase; font-size: 10px; }
tr:hover td { background: var(--card-hover); }
.badge { padding: 4px 8px; border-radius: 4px; font-size: 10px; font-weight: 700; text-transform: uppercase; }
</style>
<div class="header">
  <div class="title-area">
    <h1>Аналитическая Панель</h1>
    <div class="subtitle">Сводка ключевых показателей эффективности и конверсии OLX</div>
  </div>
  <div class="nav-pills">
    <a href="/">Главная</a>
    <a href="/stats">Вчерашняя</a>
    <a href="/weekly">Еженедельная</a>
    <a href="/dashboard" class="active">Дашборд</a>
    <a href="/bots">🤖 Боты</a>
    <a href="/whatsapp">💬 WhatsApp бот</a>
    <a href="/logs">📜 Логи</a>
  </div>
</div>

<script>
function switchTab(tabId) {
    document.getElementById('tab-olx').style.display = (tabId === 'olx') ? 'block' : 'none';
    document.getElementById('tab-bot').style.display = (tabId === 'bot') ? 'block' : 'none';
    
    // Highlight the selected card
    document.getElementById('card-bot').style.borderColor = (tabId === 'bot') ? 'var(--accent)' : 'var(--border)';
    document.getElementById('card-olx').style.borderColor = (tabId === 'olx') ? 'var(--accent)' : 'var(--border)';
}
</script>

<div class="grid-4">
  <div id="card-bot" class="card" style="border-color:var(--border); cursor:pointer;" onclick="switchTab('bot')">
    <div class="kpi-head"><span style="color:var(--accent);">Работа ботов (Сегодня)</span><div class="kpi-icon" style="background:var(--accent);color:#000">🤖</div></div>
    <div class="kpi-val">{bot_runs}</div>
    <div class="kpi-trend" style="color:var(--muted)">Успешно: {bot_succ} | Част.успех: <span style="color:#f1c40f">{bot_warn}</span> | Сбои: {bot_err}</div>
  </div>
  <div id="card-olx" class="card" style="border-color:var(--accent); cursor:pointer;" onclick="switchTab('olx')">
    <div class="kpi-head"><span>Просмотры (за неделю)</span><div class="kpi-icon">👁</div></div>
    <div class="kpi-val">{total_views}</div>
    <div class="kpi-trend {trend_views_class}">{trend_views_str} с прошлой недели</div>
  </div>
  <div class="card">
    <div class="kpi-head"><span>Конверсия в лиды</span><div class="kpi-icon" style="background:rgba(58,134,255,0.1);color:#3a86ff">📈</div></div>
    <div class="kpi-val">{conv_pct}%</div>
    <div class="bar-bg"><div class="bar-fill" style="width:{conv_pct}%; background:#3a86ff"></div></div>
  </div>
  <div class="card">
    <div class="kpi-head"><span>Всего обращений</span><div class="kpi-icon" style="background:rgba(224,179,65,0.1);color:#e0b341">📞</div></div>
    <div class="kpi-val">{total_leads}</div>
    <div class="kpi-trend" style="color:var(--muted)">Активных объявлений: {active_ads}</div>
  </div>
</div>

<div id="tab-olx">
  <div class="grid-2">
    <div class="card">
      <h3 style="font-size:14px;color:#fff">Динамика просмотров (Ежедневная)</h3>
      <div class="chart-wrap"><canvas id="mainChart"></canvas></div>
    </div>
    <div class="card">
      <h3 style="font-size:14px;color:#fff;margin-bottom:24px">Каналы обращений</h3>
      <div class="ch-row" style="margin-top:0"><span>Звонки (Телефоны)</span> <span style="color:#16c79a">{phones} ({phones_pct}%)</span></div>
      <div class="bar-bg"><div class="bar-fill" style="width:{phones_pct}%;background:#16c79a"></div></div>
      <div class="ch-row"><span>Сообщения (Чаты)</span> <span style="color:#3a86ff">{chats} ({chats_pct}%)</span></div>
      <div class="bar-bg"><div class="bar-fill" style="width:{chats_pct}%;background:#3a86ff"></div></div>
      <div class="ch-row" style="margin-top:32px;color:var(--muted);font-weight:400;font-size:11px">
        Данные основаны на суммарной статистике за текущую неделю по всем активным объявлениям.
      </div>
    </div>
  </div>

  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <h3 style="font-size:14px;color:#fff">ТОП-10 Активных объявлений (По лидам)</h3>
      <a href="/weekly" style="font-size:12px;color:var(--accent);font-weight:700">Все объявления →</a>
    </div>
    <table>
      <thead><tr><th>ID</th><th>Объявление</th><th>Город</th><th style="text-align:right">👁 Просм.</th><th style="text-align:right">📞 Лиды</th><th style="text-align:right">Конв.</th></tr></thead>
      <tbody>{top_ads_html}</tbody>
    </table>
  </div>
</div>

<div id="tab-bot" style="display:none;">
  <div class="grid-2">
    <div class="card">
      <h3 style="font-size:14px;color:#fff">Динамика запусков ботов</h3>
      <div class="chart-wrap"><canvas id="botChart"></canvas></div>
    </div>
    <div class="card">
      <h3 style="font-size:14px;color:#fff;margin-bottom:24px">Статус выполнения задач</h3>
      <div class="ch-row" style="margin-top:0"><span>Успешные действия</span> <span style="color:#16c79a">{bot_succ_pct}%</span></div>
      <div class="bar-bg"><div class="bar-fill" style="width:{bot_succ_pct}%;background:#16c79a"></div></div>
      <div class="ch-row"><span>Частичный успех</span> <span style="color:#f1c40f">{bot_warn_pct}%</span></div>
      <div class="bar-bg"><div class="bar-fill" style="width:{bot_warn_pct}%;background:#f1c40f"></div></div>
      <div class="ch-row"><span>Ошибки / Сбои</span> <span style="color:var(--danger)">{bot_err_pct}%</span></div>
      <div class="bar-bg"><div class="bar-fill" style="width:{bot_err_pct}%;background:var(--danger)"></div></div>
      <div class="ch-row" style="margin-top:24px; padding-top:16px; border-top:1px solid var(--border);">
        <span>Расход трафика прокси (за сутки)</span> 
        <span style="color:#f1c40f; font-weight:800;">{bot_traffic_mb} МБ</span>
      </div>
    </div>
  </div>
  
  <div class="grid-2" style="margin-top:16px;">
    <div class="card">
      <h3 style="font-size:14px;color:#fff;margin-bottom:16px">Успешные действия по пачкам</h3>
      <div class="chart-wrap" style="height:250px; display:flex; justify-content:center;"><canvas id="pieChart"></canvas></div>
    </div>
    <div class="card">
      <h3 style="font-size:14px;color:#fff;margin-bottom:16px">Сводка по пачкам (Batches)</h3>
      <div id="dynamic-batches-summary" style="display:grid; grid-template-columns: 1fr; gap: 16px; max-height:250px; overflow-y:auto; padding-right:8px;">
        <div style="color:var(--muted); font-size:12px;">Откройте пачки ниже, чтобы увидеть их сводку здесь</div>
      </div>
    </div>
  </div>

  <div class="card" style="margin-top:16px;">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <h3 style="font-size:14px;color:#fff">Сводка по каждой странице</h3>
      <select id="bot-ad-select" onchange="filterBotStats(this.value)" style="background:var(--bg); border:1px solid var(--border); color:#fff; padding:4px 8px; border-radius:4px; font-size:12px; max-width:300px;">
          <option value="ALL">Все объявления (Суммарно)</option>
          {bot_ad_options}
      </select>
    </div>
    <div id="bot-stats-grid" style="margin-top: 16px;">
      {bot_ads_table_html}
    </div>
  </div>
</div>

<script>
function filterBotStats(urlHash) {
    const rows = document.querySelectorAll('.bot-stat-row');
    rows.forEach(r => {
        if (urlHash === 'ALL' || r.getAttribute('data-hash') === urlHash) {
            r.style.display = '';
        } else {
            r.style.display = 'none';
        }
    });
}
const ctx = document.getElementById('mainChart').getContext('2d');
let gradient = ctx.createLinearGradient(0, 0, 0, 300);
gradient.addColorStop(0, 'rgba(22, 199, 154, 0.4)');
gradient.addColorStop(1, 'rgba(22, 199, 154, 0.0)');
new Chart(ctx, {
  type: 'line',
  data: {
    labels: {chart_labels},
    datasets: [{
      label: 'Просмотры',
      data: {chart_data},
      borderColor: '#16c79a',
      backgroundColor: gradient,
      borderWidth: 3,
      pointBackgroundColor: '#16c79a',
      pointBorderColor: '#fff',
      pointRadius: 4,
      pointHoverRadius: 6,
      fill: true,
      tension: 0.4
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { color: '#23242f', drawBorder: false }, ticks: { color: '#8b8b99', font: { family: 'Inter', size: 10 } } },
      y: { grid: { color: '#23242f', drawBorder: false }, ticks: { color: '#8b8b99', font: { family: 'Inter', size: 10 }, beginAtZero: true } }
    }
  }
});

const botCtx = document.getElementById('botChart').getContext('2d');
new Chart(botCtx, {
  type: 'bar',
  data: {
    labels: {bot_chart_labels},
    datasets: [{
      label: 'Успешно',
      data: {bot_chart_data_succ},
      backgroundColor: '#16c79a',
      borderRadius: 4
    },
    {
      label: 'Ошибки',
      data: {bot_chart_data_err},
      backgroundColor: '#ff5d5d',
      borderRadius: 4
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    onClick: function(evt, activeElements) {
      if (activeElements.length > 0) {
        var dataIndex = activeElements[0].index;
        var label = this.data.labels[dataIndex]; // "07-07"
        var year = new Date().getFullYear();
        window.location.href = '/dashboard?bot_date=' + year + '-' + label;
      }
    },
    interaction: {
      mode: 'index',
      intersect: false
    },
    plugins: { 
      legend: { display: true, labels: { color: '#8b8b99', font: { size: 10 } } },
      tooltip: {
        callbacks: {
          label: function(context) {
            return context.dataset.label + ': ' + context.raw;
          }
        }
      }
    },
    scales: {
      x: { stacked: true, grid: { color: '#23242f', drawBorder: false }, ticks: { color: '#8b8b99', font: { family: 'Inter', size: 10 } } },
      y: { stacked: true, grid: { color: '#23242f', drawBorder: false }, ticks: { color: '#8b8b99', font: { family: 'Inter', size: 10 }, beginAtZero: true } }
    }
  }
});

const pieCtx = document.getElementById('pieChart').getContext('2d');
window.botPieChart = new Chart(pieCtx, {
  type: 'doughnut',
  data: {
    labels: {bot_pie_labels},
    datasets: [{
      data: {bot_pie_data},
      backgroundColor: ['#16c79a', '#f1c40f', '#3498db', '#e74c3c', '#9b59b6', '#34495e', '#1abc9c', '#e67e22', '#ff5d5d', '#2ecc71'],
      borderWidth: 0,
      hoverOffset: 4
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'right', labels: { color: '#8b8b99', font: { family: 'Inter', size: 10 } } },
      tooltip: {
        callbacks: {
          label: function(context) {
            return ' ' + context.label + ': ' + context.raw + ' успехов';
          }
        }
      }
    }
  }
});

function updateChartsForOpenBatches() {
    const openDetails = document.querySelectorAll('.batch-details[open]');
    let newLabels = [];
    let newData = [];
    let summaryHtml = "";
    
    // If no batches are open, we fall back to all batches or just empty stats? 
    // The user requested: "если вместе то стата открытых в виде круга", let's make it show ALL if NONE is open, or JUST the opened ones if ANY is open.
    let targetDetails = openDetails.length > 0 ? openDetails : document.querySelectorAll('.batch-details');
    
    targetDetails.forEach(d => {
        let name = d.getAttribute('data-batch-name');
        let succ = parseInt(d.getAttribute('data-batch-succ')) || 0;
        let warn = parseInt(d.getAttribute('data-batch-warn')) || 0;
        let err = parseInt(d.getAttribute('data-batch-err')) || 0;
        
        if (succ > 0) {
            newLabels.push(name);
            newData.push(succ);
        }
        
        if (openDetails.length > 0) {
            let total = succ + warn + err;
            let succPct = total > 0 ? (succ / total * 100).toFixed(1) : 0;
            let warnPct = total > 0 ? (warn / total * 100).toFixed(1) : 0;
            let errPct = total > 0 ? (err / total * 100).toFixed(1) : 0;
            
            summaryHtml += `
            <div class="bot-stat-row card" style="background:var(--bg); border:1px solid var(--border); padding:16px; margin-bottom:12px;">
                <div style="font-size:12px; margin-bottom:8px; font-weight:bold; color:var(--accent);">
                    ${name}
                </div>
                <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:4px; color:var(--muted);">
                    <span>Успешно</span> <b>${succ}</b>
                </div>
                <div class="bar-bg" style="margin-bottom:8px; height:4px;"><div class="bar-fill" style="width:${succPct}%;background:#16c79a"></div></div>
                
                <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:4px; color:var(--muted);">
                    <span>Частичный успех</span> <b>${warn}</b>
                </div>
                <div class="bar-bg" style="margin-bottom:8px; height:4px;"><div class="bar-fill" style="width:${warnPct}%;background:#f1c40f"></div></div>
                
                <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:4px; color:var(--muted);">
                    <span>Ошибки</span> <b>${err}</b>
                </div>
                <div class="bar-bg" style="height:4px;"><div class="bar-fill" style="width:${errPct}%;background:var(--danger)"></div></div>
            </div>`;
        }
    });
    
    window.botPieChart.data.labels = newLabels;
    window.botPieChart.data.datasets[0].data = newData;
    window.botPieChart.update();
    
    let batchesContainer = document.getElementById('dynamic-batches-summary');
    if (batchesContainer) {
        if (openDetails.length > 0) {
            batchesContainer.innerHTML = summaryHtml;
        } else {
            batchesContainer.innerHTML = '<div style="color:var(--muted); font-size:12px;">Откройте пачки ниже, чтобы увидеть их детальную сводку здесь</div>';
        }
    }
}

document.querySelectorAll('.batch-details').forEach(d => {
    d.addEventListener('toggle', updateChartsForOpenBatches);
});
setTimeout(updateChartsForOpenBatches, 50);

// Live update for single ad progress in dashboard
async function updateDashboardLiveProgress() {
    try {
        const r = await fetch('/bots/status');
        const res = await r.json();
        
        document.querySelectorAll('.single-live-progress').forEach(bar => {
            let u = bar.getAttribute('data-url') || "";
            let uAliases = u.split(" ").filter(Boolean);
            
            let activeCount = 0;
            let waitingCount = 0;
            let finishedCount = 0;
            let totalCount = 0;
            
            for (const [tid, t] of Object.entries(res)) {
                let tUrl = String(t.url || "").trim();
                let isFinished = (t.status || "").toLowerCase().includes("завершено") || (t.status || "").toLowerCase().includes("ошибк");
                let isWaiting = (t.status || "").toLowerCase().includes("ожидание") || (t.status || "").toLowerCase().includes("очереди");
                
                if (tUrl) {
                    let isMatch = false;
                    for (let alias of uAliases) {
                        if (tUrl.includes(alias) || alias.includes(tUrl)) {
                            isMatch = true;
                            break;
                        }
                    }
                    if (isMatch) {
                        totalCount++;
                        if (isFinished) {
                            finishedCount++;
                        } else if (isWaiting) {
                            waitingCount++;
                        } else {
                            activeCount++;
                        }
                    }
                }
            }
            
            let countEl = bar.querySelector('.single-live-count');
            let fillEl = bar.querySelector('.bar-fill');
            
            if (countEl) {
                if (totalCount > 0) {
                    countEl.innerHTML = `<span style="color:#16c79a">${activeCount} активных</span> <span style="color:var(--muted); font-weight:normal;">/ ${totalCount} задано</span>`;
                } else {
                    countEl.innerHTML = `<span style="color:var(--blue); font-weight:bold;">0</span>`;
                }
            }
            if (fillEl) {
                if (totalCount > 0) {
                    fillEl.style.width = '100%';
                    fillEl.style.opacity = activeCount > 0 ? '1' : '0.5';
                    fillEl.style.animation = activeCount > 0 ? 'progress-stripes 1s linear infinite' : 'none';
                } else {
                    fillEl.style.width = '0%';
                    fillEl.style.opacity = '1';
                    fillEl.style.animation = 'none';
                }
            }
        });
    } catch(e) {}
}
setInterval(updateDashboardLiveProgress, 2000);
setTimeout(updateDashboardLiveProgress, 500);
</script>
"""

@app.get("/dashboard")
def custom_dashboard():
    import json, datetime
    bot_date = request.args.get("bot_date", "")
    # Get items for current week
    items, start, end = _weekly_data("this")
    
    active_ads = len(items)
    total_views = sum(it.get("dv") or 0 for it in items)
    total_phones = sum(it.get("dp") or 0 for it in items)
    
    # We need chat data, which is leads - phones
    total_leads = sum(it.get("leads") or 0 for it in items)
    total_chats = total_leads - total_phones
    
    strong_ads = sum(1 for it in items if it.get("vk") == "strong")
    
    conv_pct = (total_leads / total_views * 100) if total_views > 0 else 0
    
    # Prev week for trend
    p_items, _, _ = _weekly_data("prev")
    p_views = sum(it.get("dv") or 0 for it in p_items)
    
    diff_views = total_views - p_views
    diff_pct = (diff_views / p_views * 100) if p_views > 0 else 100
    
    if diff_views > 0:
        trend_views_class = "up"
        trend_views_str = f"↗ +{diff_pct:.1f}%"
    elif diff_views < 0:
        trend_views_class = "down"
        trend_views_str = f"↘ {diff_pct:.1f}%"
    else:
        trend_views_class = ""
        trend_views_str = "0%"

    phones_pct = (total_phones / total_leads * 100) if total_leads > 0 else 0
    chats_pct = (total_chats / total_leads * 100) if total_leads > 0 else 0
    
    # Top 10 ads
    top_ads = sorted(items, key=lambda x: (x.get("leads") or 0), reverse=True)[:10]
    top_ads_html = ""
    for ad in top_ads:
        url = ad.get("url") or f"/advert/{ad['id']}"
        title = (ad.get("title") or "—")[:50]
        id_cell = f"<a href='{url}' target='_blank' style='color:var(--text);font-family:monospace'>{ad['id']}</a>"
        conv = ad.get("conv") or "0%"
        top_ads_html += f"<tr><td>{id_cell}</td><td>{title}</td><td>{ad.get('city') or '—'}</td><td style='text-align:right'>{ad.get('dv') or 0}</td><td style='text-align:right;color:#16c79a;font-weight:700'>{ad.get('leads') or 0}</td><td style='text-align:right'>{conv}</td></tr>"
        
    if not top_ads_html:
        top_ads_html = "<tr><td colspan='6' style='text-align:center;color:var(--muted)'>Нет данных за этот период</td></tr>"
        
    # Chart data - let's fetch daily views for active ads from storage
    # We will get last 7 days of total views
    c = storage.conn()
    seven_days_ago = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    rows = c.execute("SELECT day, SUM(advert_views) as sum_v FROM stats WHERE day >= ? GROUP BY day ORDER BY day", (seven_days_ago,)).fetchall()
    c.close()
    
    # compute daily diffs since stats table has absolute values or daily values?
    # Actually, stats table stores cumulative views. We need daily differences!
    # Wait, the history chart does h["advert_views"] - pv.
    # We can just fetch total cumulative views per day and diff them.
    # To keep it simple, if no daily data, we will just show a flat line or dummy
    # Let's use simple logic: Just pass dummy data if not available, or extract from weekly logic.
    chart_labels = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    chart_data = [total_views // 7] * 7 # Fallback flat line
    
    if len(rows) > 1:
        c_labels = []
        c_data = []
        prev_v = None
        for r in rows:
            day_str = r["day"]
            v = r["sum_v"]
            if prev_v is not None:
                c_labels.append(day_str[-5:]) # MM-DD
                c_data.append(max(0, v - prev_v))
            prev_v = v
        if c_labels:
            chart_labels = c_labels[-7:]
            chart_data = c_data[-7:]


    try:
        import bots.interaction as bot
        import hashlib
        
        all_dates = bot.get_all_stat_dates()
        if bot_date not in all_dates and all_dates:
            bot_date = all_dates[0]
            
        bst = bot.get_stats_for_date(bot_date)
        bot_runs = bst.get("runs", 0)
        bot_succ = bst.get("success", 0)
        bot_warn = bst.get("warnings", 0)
        bot_err = bst.get("errors", 0)
        bot_traffic_mb = bst.get("traffic_mb", 0.0)
        bot_urls = bst.get("urls", {})
        
        import os
        parsed_groups = {}
        current_batch = "Прочие (не из пачек)"
        if os.path.exists("links.txt"):
            with open("links.txt", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    if line.startswith("http"):
                        parsed_groups.setdefault(current_batch, []).append(line)
                    elif "," in line or line.isdigit():
                        ids = [x.strip() for x in line.replace(" (снято)", "").split(",") if x.strip().isdigit()]
                        if ids:
                            parsed_groups.setdefault(current_batch, []).extend(ids)
                    elif "ПАЧКА" in line.upper() or "📦" in line or "🎯" in line or "MIX" in line.upper() or "ТЕСТ" in line.upper():
                        current_batch = line.replace("📦", "").replace("🎯", "").replace("───────────────────────────────────────────", "").strip()
                        current_batch = current_batch.split("—")[0].strip()
        
        def encode_olx_id(num_str):
            try:
                base62 = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
                num = int(num_str)
                if num == 0: return '0'
                res = ''
                while num > 0:
                    res = base62[num % 62] + res
                    num //= 62
                return "ID" + res
            except:
                return num_str

        final_groups = {}
        for b_name, b_items in parsed_groups.items():
            final_groups[b_name] = []
            for item in b_items:
                matched_u = None
                encoded_item = encode_olx_id(item)
                for u in bot_urls.keys():
                    if item in u or encoded_item in u:
                        matched_u = u
                        break
                if matched_u:
                    final_groups[b_name].append(matched_u)
                else:
                    final_groups[b_name].append(item)
                    
        final_groups.setdefault("Прочие (не из пачек)", [])
        matched_urls = set()
        for b_name, b_items in final_groups.items():
            if b_name != "Прочие (не из пачек)":
                matched_urls.update(b_items)
                
        for u in bot_urls.keys():
            if u not in matched_urls:
                final_groups["Прочие (не из пачек)"].append(u)
        
        bot_ad_options = ""
        bot_ads_table_html = ""
        
        for batch_name, batch_links_with_stats in final_groups.items():
            batch_success = sum([bot_urls.get(u, {}).get("success", 0) for u in batch_links_with_stats])
            batch_runs = sum([bot_urls.get(u, {}).get("runs", 0) for u in batch_links_with_stats])
            batch_warn = sum([bot_urls.get(u, {}).get("warnings", 0) for u in batch_links_with_stats])
            batch_err = sum([bot_urls.get(u, {}).get("errors", 0) for u in batch_links_with_stats])
            
            b_succ_pct = (batch_success / batch_runs * 100) if batch_runs > 0 else 0
            b_warn_pct = (batch_warn / batch_runs * 100) if batch_runs > 0 else 0
            b_err_pct = (batch_err / batch_runs * 100) if batch_runs > 0 else 0

            bot_ads_table_html += f'''
            <details class="batch-details" data-batch-name="{batch_name}" data-batch-succ="{batch_success}" data-batch-warn="{batch_warn}" data-batch-err="{batch_err}" style="margin-bottom:16px; background:var(--bg); border:1px solid var(--border); border-radius:8px;">
                <summary style="padding:16px; cursor:pointer; list-style:none; display:flex; justify-content:space-between; align-items:center;">
                    <div style="min-width: 250px;">
                        <span style="font-weight:bold; color:var(--accent); font-size:14px;">{batch_name}</span> 
                        <span style="color:var(--muted); font-size:12px; margin-left:6px;">({len(batch_links_with_stats)} объявлений)</span>
                    </div>
                    
                    <div style="flex:1; margin:0 20px; max-width:400px;">
                        <div style="display:flex; height:6px; border-radius:3px; background:#15161c; overflow:hidden; border:1px solid var(--border);">
                            <div style="width:{b_succ_pct}%; background:#16c79a;" title="Успех: {batch_success}"></div>
                            <div style="width:{b_warn_pct}%; background:#f1c40f;" title="Частично: {batch_warn}"></div>
                            <div style="width:{b_err_pct}%; background:var(--danger);" title="Ошибки: {batch_err}"></div>
                        </div>
                        <div style="font-size:10px; color:var(--muted); display:flex; justify-content:space-between; margin-top:6px;">
                            <span>Всего запусков: <b style="color:var(--text)">{batch_runs}</b></span>
                            <span>Успешно: <b style="color:#16c79a">{batch_success} ({b_succ_pct:.1f}%)</b></span>
                        </div>
                    </div>

                    <span style="color:var(--muted); font-size:10px; background:rgba(255,255,255,0.05); padding:4px 8px; border-radius:4px; border:1px solid var(--border); white-space:nowrap;">▼ Раскрыть / Скрыть</span>
                </summary>
                <div style="padding:0 16px 16px 16px; display:grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 16px; border-top:1px solid rgba(255,255,255,0.05); padding-top:16px;">
            '''
            
            for u in batch_links_with_stats:
                s = bot_urls.get(u, {})
                h = hashlib.md5(u.encode()).hexdigest()
                display_name = u
                
                original_id = u
                for raw_id in parsed_groups.get(batch_name, []):
                    if raw_id in u or encode_olx_id(raw_id) in u:
                        original_id = raw_id
                        break
                        
                encoded_id = encode_olx_id(original_id.strip())
                data_urls = f"{original_id.strip()} {encoded_id} {u.strip()}"
                
                try:
                    if "/d/obyavlenie/" in u:
                        display_name = "OLX: " + u.split("-ID")[1].split(".html")[0]
                except: pass
                
                bot_ad_options += f'<option value="{h}">{display_name}</option>'
                
                u_runs = s.get("runs", 0)
                u_succ = s.get("success", 0)
                u_warn = s.get("warnings", 0)
                u_err = s.get("errors", 0)
                
                u_succ_pct_num = (u_succ / u_runs * 100) if u_runs > 0 else 0
                u_warn_pct_num = (u_warn / u_runs * 100) if u_runs > 0 else 0
                u_err_pct_num = (u_err / u_runs * 100) if u_runs > 0 else 0
                
                ips_list = s.get("ips", [])
                ips_html = "".join([f'<div style="font-size:10px; color:var(--muted); padding:2px 0; border-bottom:1px solid #23242f;">{ip.replace("http://","").replace("socks5://","")}</div>' for ip in ips_list if ip])
                if not ips_html:
                    ips_html = '<div style="font-size:10px; color:var(--muted);">Прямой IP (195.245.96.252)</div>'
                    
                actions = s.get("actions", {"scroll": 0, "phone": 0, "chat": 0})
                scrolls = actions.get("scroll", 0)
                phones = actions.get("phone", 0)
                chats = actions.get("chat", 0)
                bot_ads_table_html += f'''
                <div class="bot-stat-row card" data-hash="{h}" style="background:var(--bg); border:1px solid var(--border); padding:16px; margin:0;">
                    <div style="font-size:11px; margin-bottom:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                        <a href="{u}" target="_blank" style="color:var(--blue);">{display_name}</a>
                    </div>
                    
                    <div class="single-live-progress" data-url="{data_urls}" style="margin-bottom:12px;">
                        <div class="ch-row" style="margin-bottom:4px; font-size:11px;"><span>В работе</span> <span class="single-live-count" style="color:var(--blue); font-weight:bold;">0</span></div>
                        <div class="bar-bg" style="background:rgba(58,134,255,0.1);"><div class="bar-fill" style="width:0%; background:var(--blue); background-image:linear-gradient(45deg,rgba(255,255,255,.15) 25%,transparent 25%,transparent 50%,rgba(255,255,255,.15) 50%,rgba(255,255,255,.15) 75%,transparent 75%,transparent); background-size:1rem 1rem;"></div></div>
                    </div>
                    
                    <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
                        <span style="color:var(--muted)">Всего зашло ботов</span> <b>{u_runs}</b>
                    </div>
                    
                    <div class="ch-row" style="margin-top:12px; font-size:11px;"><span>Успешно ({u_succ})</span> <span style="color:#16c79a">{u_succ_pct_num:.1f}%</span></div>
                    <div class="bar-bg"><div class="bar-fill" style="width:{u_succ_pct_num}%;background:#16c79a"></div></div>
                    
                    <div class="ch-row" style="margin-top:12px; font-size:11px;"><span>Частично ({u_warn})</span> <span style="color:#f1c40f">{u_warn_pct_num:.1f}%</span></div>
                    <div class="bar-bg"><div class="bar-fill" style="width:{u_warn_pct_num}%;background:#f1c40f"></div></div>
                    
                    <div class="ch-row" style="margin-top:12px; font-size:11px;"><span>Ошибки ({u_err})</span> <span style="color:var(--danger)">{u_err_pct_num:.1f}%</span></div>
                    <div class="bar-bg"><div class="bar-fill" style="width:{u_err_pct_num}%;background:var(--danger)"></div></div>
                    
                    <div style="margin-top:16px; padding-top:12px; border-top:1px solid var(--border);">
                        <div style="font-size:11px; color:#fff; margin-bottom:8px;">Успешно выполнено:</div>
                        <div style="display:flex; justify-content:space-between; font-size:10px; margin-bottom:4px; color:var(--muted);">
                            <span>Скроллинг (чтение)</span> <b style="color:var(--text)">{scrolls}</b>
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:10px; margin-bottom:4px; color:var(--muted);">
                            <span>Нажатий "Показать телефон"</span> <b style="color:var(--text)">{phones}</b>
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:10px; margin-bottom:4px; color:var(--muted);">
                            <span>Открытий чата / Сообщений</span> <b style="color:var(--text)">{chats}</b>
                        </div>
                    </div>
                    
                    <div style="margin-top:12px; text-align:center;">
                        <button onclick="document.getElementById('ips-{h}').style.display = document.getElementById('ips-{h}').style.display === 'none' ? 'block' : 'none';" style="background:none; border:1px solid var(--border); color:var(--muted); padding:4px 8px; border-radius:4px; font-size:10px; cursor:pointer; width:100%;">Показать использованные IP ▼</button>
                    </div>
                    <div id="ips-{h}" style="display:none; margin-top:8px; max-height:100px; overflow-y:auto; padding:8px; background:#15161c; border-radius:4px;">
                        {ips_html}
                    </div>
                </div>
                '''
            bot_ads_table_html += "</div></details>"
            
        bot_succ_pct = (bot_succ / bot_runs * 100) if bot_runs > 0 else 0
        bot_warn_pct = (bot_warn / bot_runs * 100) if bot_runs > 0 else 0
        bot_err_pct = (bot_err / bot_runs * 100) if bot_runs > 0 else 0
        
        bot_batches_html = ""
        bot_pie_labels = []
        bot_pie_data = []
        try:
            import os
            if os.path.exists("links.txt"):
                with open("links.txt", "r", encoding="utf-8") as f:
                    content = f.read()
                
                curr_city = "Свои ссылки"
                curr_batch_city = "Свои ссылки"
                curr_batch = ""
                curr_links = []
                batches = []
                
                for line in content.splitlines():
                    line = line.strip()
                    if not line: continue
                    if line.startswith("http"):
                        curr_links.append(line)
                    elif "ПАЧКА" in line.upper() or "📦" in line or "🎯" in line or "MIX" in line.upper():
                        if curr_batch and curr_links:
                            batches.append((curr_batch_city, curr_batch, curr_links))
                        curr_batch = line.replace("📦", "").replace("🎯", "").replace("───────────────────────────────────────────", "").strip()
                        curr_batch = curr_batch.split("—")[0].strip()
                        curr_links = []
                        
                        u_batch = curr_batch.upper()
                        if "АЛМАТЫ" in u_batch or "ALMATY" in u_batch: curr_city = "Алматы"
                        elif "КОСТАНАЙ" in u_batch: curr_city = "Костанай"
                        elif "АСТАНА" in u_batch: curr_city = "Астана"
                        elif "ПАВЛОДАР" in u_batch or "PAVLODAR" in u_batch: curr_city = "Павлодар"
                        elif "ШЫМКЕНТ" in u_batch or "SHYMKENT" in u_batch: curr_city = "Шымкент"
                        
                        curr_batch_city = curr_city
                    elif "КОСТАНАЙ" in line.upper(): curr_city = "Костанай"
                    elif "АСТАНА" in line.upper() or "Астана" in line: curr_city = "Астана"
                    elif "АЛМАТЫ" in line.upper() or "ALMATY" in line.upper(): curr_city = "Алматы"
                    elif "ПАВЛОДАР" in line.upper() or "PAVLODAR" in line.upper(): curr_city = "Павлодар"
                    elif "ШЫМКЕНТ" in line.upper() or "SHYMKENT" in line.upper(): curr_city = "Шымкент"
                if curr_batch and curr_links:
                    batches.append((curr_batch_city, curr_batch, curr_links))
                
                for city, batch_name, links in batches:
                    b_succ = 0
                    b_warn = 0
                    b_err = 0
                    for u in links:
                        st = bot_urls.get(u, {})
                        b_succ += st.get("success", 0)
                        b_warn += st.get("warnings", 0)
                        b_err += st.get("errors", 0)
                    b_runs = b_succ + b_warn + b_err
                    if b_runs > 0:
                        b_succ_pct = (b_succ / b_runs) * 100
                        b_warn_pct = (b_warn / b_runs) * 100
                        b_err_pct = (b_err / b_runs) * 100
                    else:
                        b_succ_pct = 0
                        b_warn_pct = 0
                        b_err_pct = 0
                        
                    if b_succ > 0:
                        bot_pie_labels.append(f"{city} — {batch_name}")
                        bot_pie_data.append(b_succ)
                        
                    bot_batches_html += f'''
                    <div class="bot-stat-row card" style="background:var(--bg); border:1px solid var(--border); padding:16px;">
                        <div style="font-size:12px; margin-bottom:8px; font-weight:bold; color:var(--accent);">
                            {city} — {batch_name}
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:4px; color:var(--muted);">
                            <span>Успешно</span> <b>{b_succ}</b>
                        </div>
                        <div class="bar-bg" style="margin-bottom:8px; height:4px;"><div class="bar-fill" style="width:{b_succ_pct}%;background:#16c79a"></div></div>
                        
                        <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:4px; color:var(--muted);">
                            <span>Частичный успех</span> <b>{b_warn}</b>
                        </div>
                        <div class="bar-bg" style="margin-bottom:8px; height:4px;"><div class="bar-fill" style="width:{b_warn_pct}%;background:#f1c40f"></div></div>
                        
                        <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:4px; color:var(--muted);">
                            <span>Ошибки</span> <b>{b_err}</b>
                        </div>
                        <div class="bar-bg" style="height:4px;"><div class="bar-fill" style="width:{b_err_pct}%;background:var(--danger)"></div></div>
                    </div>
                    '''
            if not bot_batches_html:
                bot_batches_html = '<div style="color:var(--muted); font-size:12px;">Нет данных по пачкам</div>'
        except Exception as e:
            bot_batches_html = f'<div style="color:var(--danger); font-size:12px;">Ошибка загрузки пачек: {e}</div>'

        
        # In a real app we'd fetch historical bot data. For now, just show the last 7 days from the JSON or dummy data if unavailable.
        bot_chart_labels = []
        bot_chart_data_succ = []
        bot_chart_data_err = []
        
        try:
            import os
            import json
            import datetime
            if os.path.exists("static/live/stats.json"):
                with bot.stats_lock:
                    with open("static/live/stats.json", "r") as f:
                        all_st = json.load(f)
                
                # Get last 7 days
                today_dt = datetime.date.today()
                for i in range(6, -1, -1):
                    d = (today_dt - datetime.timedelta(days=i)).isoformat()
                    bot_chart_labels.append(d[-5:])
                    if d in all_st:
                        bot_chart_data_succ.append(all_st[d].get("success", 0))
                        bot_chart_data_err.append(all_st[d].get("errors", 0))
                    else:
                        bot_chart_data_succ.append(0)
                        bot_chart_data_err.append(0)
        except:
            bot_chart_labels = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            bot_chart_data_succ = [0]*7
            bot_chart_data_err = [0]*7

    except Exception as e:
        print("DASHBOARD ERROR:", e)
        import traceback
        traceback.print_exc()
        bot_runs = bot_succ = bot_warn = bot_err = 0
        bot_traffic_mb = 0.0
        bot_succ_pct = bot_warn_pct = bot_err_pct = 0
        bot_ad_options = ""
        bot_batches_html = ""
        bot_ads_table_html = "<tr><td colspan='5' style='text-align:center;color:var(--danger)'>Ошибка загрузки статистики</td></tr>"
        bot_chart_labels = []
        bot_chart_data_succ = []
        bot_chart_data_err = []
        bot_pie_labels = []
        bot_pie_data = []
        try:
            bot_date = bot_date or datetime.date.today().isoformat()
            all_dates = [bot_date]
        except:
            all_dates = []
        
    ds_html = f'<div style="margin-bottom:16px;"><select onchange="window.location.href=\'/dashboard?bot_date=\'+this.value" style="padding:8px; border-radius:4px; background:#15161c; color:#fff; border:1px solid #23242f; cursor:pointer;">'
    for d in all_dates:
        sel = "selected" if d == bot_date else ""
        ds_html += f'<option value="{d}" {sel}>Статистика ботов за: {d}</option>'
    ds_html += '</select></div>'
        
    bot_stats_html = ds_html + f'''<div class="card" style="border-color:var(--accent);">
    <div class="kpi-head"><span style="color:var(--accent);">Работа ботов ({bot_date})</span><div class="kpi-icon" style="background:var(--accent);color:#000">🤖</div></div>
    <div class="kpi-val">{bot_runs}</div>
    <div class="kpi-trend" style="color:var(--muted)">Успешно: {bot_succ} | Част.успех: <span style="color:#f1c40f">{bot_warn}</span> | Сбои: {bot_err}</div>
    <div style="margin-top:10px; font-size:12px; color:var(--text); padding-top:10px; border-top:1px solid var(--border);">Расход трафика: <b style="color:#f1c40f">{bot_traffic_mb:.2f} МБ</b></div>
  </div>'''
  
    replacements = {
        "{bot_runs}": bot_runs,
        "{bot_succ}": bot_succ,
        "{bot_warn}": bot_warn,
        "{bot_err}": bot_err,
        "{bot_traffic_mb}": f"{bot_traffic_mb:.2f}",
        "{bot_succ_pct}": f"{bot_succ_pct:.1f}",
        "{bot_warn_pct}": f"{bot_warn_pct:.1f}",
        "{bot_err_pct}": f"{bot_err_pct:.1f}",
        "{bot_batches_html}": bot_batches_html,
        "{bot_pie_labels}": json.dumps(bot_pie_labels),
        "{bot_pie_data}": json.dumps(bot_pie_data),
        "{bot_chart_labels}": json.dumps(bot_chart_labels),
        "{bot_chart_data_succ}": json.dumps(bot_chart_data_succ),
        "{bot_chart_data_err}": json.dumps(bot_chart_data_err),
        "{bot_ad_options}": bot_ad_options,
        "{bot_ads_table_html}": bot_ads_table_html,
        "{bot_stats_html}": bot_stats_html,
        "{total_views}": total_views,
        "{trend_views_class}": trend_views_class,
        "{trend_views_str}": trend_views_str,
        "{conv_pct}": f"{conv_pct:.1f}",
        "{total_leads}": total_leads,
        "{active_ads}": active_ads,
        "{strong_ads}": strong_ads,
        "{phones}": total_phones,
        "{phones_pct}": f"{phones_pct:.1f}",
        "{chats}": total_chats,
        "{chats_pct}": f"{chats_pct:.1f}",
        "{top_ads_html}": top_ads_html,
        "{chart_labels}": json.dumps(chart_labels),
        "{chart_data}": json.dumps(chart_data)
    }
    out = DASHBOARD_HTML
    for k, v in replacements.items():
        out = out.replace(k, str(v))
    return out





# --- планировщик




# --- планировщик: дневной прогон ---
def _start_scheduler():
    global scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        hour = int(os.getenv("DAILY_HOUR", "23"))
        minute = int(os.getenv("DAILY_MINUTE", "55"))
        tz = os.getenv("TZ", "Asia/Almaty")
        scheduler = BackgroundScheduler(timezone=tz)
        scheduler.add_job(runner.run_all, "cron", hour=hour, minute=minute)
        scheduler.start()
        print(f"[scheduler] ежедневный сбор запланирован на {hour:02d}:{minute:02d} {tz}")
        update_scheduler_jobs()
    except Exception as e:
        print("scheduler off:", e)

_start_scheduler()



@app.get("/live/<task_id>")
def live_view(task_id):
    return f'''<!doctype html>
<meta charset="utf-8">
<title>Live View: {task_id}</title>
<style>
body {{ background: #000; color: #fff; text-align: center; font-family: sans-serif; margin: 0; display: flex; flex-direction: column; height: 100vh; }}
.header {{ padding: 16px; background: #15161c; border-bottom: 1px solid #23242f; }}
.content {{ flex: 1; display: flex; justify-content: center; align-items: center; overflow: hidden; padding: 16px; }}
img {{ max-width: 100%; max-height: 100%; border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }}
</style>
<div class="header">
    <h3>🔴 Live: {task_id}</h3>
    <p style="color:#8b8b99;font-size:12px;margin-top:4px;">Трансляция действий бота (обновляется каждую секунду)</p>
</div>
<div class="content">
    <img id="screen" src="/live_img/{task_id}?t=0" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'400\' height=\'300\'><rect width=\'400\' height=\'300\' fill=\'%231c1d25\'/><text x=\'50%\' y=\'50%\' fill=\'%238b8b99\' dominant-baseline=\'middle\' text-anchor=\'middle\' font-family=\'sans-serif\'>Ожидание изображения...</text></svg>'" />
</div>
<script>
setInterval(() => {{
    const img = new Image();
    img.onload = () => {{ document.getElementById("screen").src = img.src; }};
    img.src = "/live_img/{task_id}?t=" + Date.now();
}}, 1000);
</script>
'''

@app.get("/live_img/<task_id>")
def live_img(task_id):
    import os
    path = os.path.join("static", "live", f"{task_id}.jpg")
    if os.path.exists(path):
        return send_file(path)
    return "Not found", 404










# --- BOTS UI ---
BOTS_HTML = """<!doctype html>
<meta charset="utf-8">
<title>Управление ботами</title>
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #0b0c10; --card: #15161c; --card-hover: #1c1d25;
  --text: #ffffff; --muted: #8b8b99;
  --accent: #16c79a; --accent-bg: rgba(22, 199, 154, 0.1);
  --border: #23242f; --danger: #ff5d5d; --blue: #3a86ff;
}
body { margin: 0; padding: 24px; background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; }
h1, h2, h3, h4 { font-family: 'Montserrat', sans-serif; text-transform: uppercase; margin: 0; }
a { color: var(--text); text-decoration: none; }
.header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 24px; }
.title-area h1 { font-size: 28px; font-weight: 800; letter-spacing: 0.5px; }
.title-area .subtitle { color: var(--muted); font-size: 13px; margin-top: 6px; font-weight: 500; }
.nav-pills { display: flex; gap: 8px; }
.nav-pills a { padding: 8px 16px; border-radius: 6px; font-size: 11px; font-weight: 700; border: 1px solid var(--border); color: var(--muted); text-transform: uppercase; transition: 0.2s; }
.nav-pills a:hover { border-color: var(--muted); }
.nav-pills a.active { background: var(--accent); color: #000; border-color: var(--accent); }
.card { background: var(--card); border-radius: 12px; padding: 20px; border: 1px solid var(--border); margin-bottom: 16px;}
table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 12px; }
th, td { padding: 12px 10px; border-bottom: 1px solid var(--border); text-align: left; }
th { color: var(--muted); font-weight: 700; text-transform: uppercase; font-size: 10px; }
tr:hover td { background: var(--card-hover); }
button { background: var(--accent); color: #000; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 13px; transition: 0.2s; }
button:hover { opacity: 0.9; transform: translateY(-1px); }
input[type=number], select, textarea { background: var(--bg); border: 1px solid var(--border); color: #fff; padding: 8px; border-radius: 4px; font-family: 'Inter'; }
textarea { width: 100%; min-height: 80px; resize: vertical; }
input[type=checkbox] { accent-color: var(--accent); width: 16px; height: 16px; margin-right: 8px; cursor: pointer;}
label { display: flex; align-items: center; cursor: pointer; font-size: 13px; margin-bottom: 8px; }
.form-group { margin-bottom: 16px; }
.form-row { display: flex; gap: 16px; align-items: flex-end; }
.grid-active { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 12px; margin-top: 12px; }
.task-card { padding: 12px; background: var(--bg); border: 1px solid var(--border); border-radius: 8px; font-size: 12px; }
.task-card b { color: var(--accent); }
</style>
<div class="header">
  <div class="title-area">
    <h1>🤖 Продвинутый запуск ботов</h1>
    <div class="subtitle">Имитация органических просмотров, распределение по времени и поддержка своих ссылок</div>
  </div>
  <div class="nav-pills">
    <a href="/">Главная</a>
    <a href="/stats">Вчерашняя</a>
    <a href="/weekly">Еженедельная</a>
    <a href="/dashboard">Дашборд</a>
    <a href="/bots" class="active">🤖 Боты</a>
    <a href="/whatsapp">💬 WhatsApp бот</a>
    <a href="/logs">📜 Логи</a>
  </div>
</div>

<div class="card">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 16px;">
    <div style="display:flex; align-items:center; gap:16px;">
        <h3 style="margin:0; text-transform:uppercase;">Задачи (<span id="active-tasks-count-header">0</span>)</h3>
        <div style="display:flex; gap:8px;">
            <button onclick="setFilter('all')" id="btn-filter-all" style="background:var(--accent); color:#000; padding:4px 12px; font-size:11px;">Все</button>
            <button onclick="setFilter('active')" id="btn-filter-active" style="background:var(--bg); color:var(--muted); border:1px solid var(--border); padding:4px 12px; font-size:11px;">В работе</button>
            <button onclick="setFilter('waiting')" id="btn-filter-waiting" style="background:var(--bg); color:var(--muted); border:1px solid var(--border); padding:4px 12px; font-size:11px;">Ожидание</button>
        </div>
    </div>
  </div>
  <div id="tasks-container" class="grid-active">Нет запущенных ботов.</div>
</div>

<div class="card">
  <h3 style="margin-bottom: 16px;">Запуск по готовым пачкам</h3>
  <div>
    {batch_cards}
  </div>
</div>

<script>
async function startBatchBot(form) {
    const btn = form.querySelector('button[type="submit"]');
    btn.disabled = true;
    const oldText = btn.innerText;
    btn.innerText = 'Запуск...';
    
    const b64urls = form.querySelector('input[name="urls_b64"]').value;
    // Base64 decode to utf-8 text (handle Unicode properly)
    const rawUrls = decodeURIComponent(escape(window.atob(b64urls)));
    
    const fd = new FormData(form);
    fd.append('urls', rawUrls);
    
    try {
        const res = await fetch('/bots/start_custom', {method:'POST', body:fd});
        const d = await res.json();
        if(d.ok) {
            btn.innerText = 'Запущено!';
            btn.style.background = 'var(--blue)';
            setTimeout(() => { btn.disabled = false; btn.innerText = oldText; btn.style.background = 'var(--accent)'; }, 2000);
            updateTasks();
        } else {
            alert('Ошибка');
            btn.disabled = false;
            btn.innerText = oldText;
        }
    } catch(e) {
        alert('Сбой сети');
        btn.disabled = false;
        btn.innerText = oldText;
    }
}
</script>

<div class="card">
  <h3 style="margin-bottom: 16px;">Запуск по своим ссылкам (ручной ввод)</h3>
  <form id="custom-bots-form" onsubmit="event.preventDefault(); startCustomBots()">
    <div class="form-group">
      <label style="font-weight:700; margin-bottom:4px; font-size:11px; text-transform:uppercase; color:var(--muted)">Ссылки на объявления (каждая с новой строки):</label>
      <textarea name="urls" placeholder="https://www.olx.kz/d/obyavlenie/...&#10;https://www.olx.kz/d/obyavlenie/..."></textarea>
    </div>
    
    <div class="form-row">
      <div class="form-group" style="flex:1">
        <label style="font-weight:700; margin-bottom:4px; font-size:11px; text-transform:uppercase; color:var(--muted)">Аккаунт:</label>
        <select name="bot_account" style="width:100%">
            <option value="guest">Гостевой (без входа)</option>
            {account_opts}
        </select>
      </div>
      <div class="form-group" style="flex:1">
        <label style="font-weight:700; margin-bottom:4px; font-size:11px; text-transform:uppercase; color:var(--muted)">Режим запуска:</label>
        <select name="mode" style="width:100%" onchange="
            const hi = document.getElementById('hours_input');
            const w = document.getElementById('work-window');
            if (this.value === 'daily') { w.style.display = 'block'; hi.value = 24; }
            else if (this.value === 'weekly') { w.style.display = 'block'; hi.value = 168; }
            else { w.style.display = 'none'; }
        ">
            <option value="fast">Быстрый (сразу)</option>
            <option value="daily">Суточный (Органический)</option>
            <option value="weekly">Недельный (Плавный за 7 дней)</option>
        </select>
      </div>
    </div>
    
    <div class="form-row">
        <div class="form-group" style="flex:1">
            <label style="font-weight:700; margin-bottom:4px; font-size:11px; text-transform:uppercase; color:var(--muted)">Количество ботов на ссылку (сутки/всего):</label>
            <input type="number" name="amount" value="5" min="1" max="1000" style="width:100%; box-sizing:border-box;">
        </div>
        <input type="hidden" name="hours" id="hours_input" value="24">
        <div class="form-group" id="work-window" style="flex:1; display:none;">
            <label style="font-weight:700; margin-bottom:4px; font-size:11px; text-transform:uppercase; color:var(--muted)">Окно работы (с - до):</label>
            <div style="display:flex; gap:8px;">
                <input type="time" name="work_start" value="08:00" style="width:50%; box-sizing:border-box; background:var(--card); color:var(--text); border:1px solid var(--border);">
                <input type="time" name="work_end" value="23:00" style="width:50%; box-sizing:border-box; background:var(--card); color:var(--text); border:1px solid var(--border);">
            </div>
        </div>
    </div>
    
    <div class="form-group" style="background:var(--bg); padding:16px; border-radius:8px; border:1px solid var(--border);">
        <label><input type="checkbox" name="scroll" checked> Скроллинг (имитация чтения, делают все боты)</label>
        
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
            <label style="margin-bottom:0;"><input type="checkbox" name="phone"> Нажатие "Показать телефон"</label>
            <div style="font-size:11px; color:var(--muted); display:flex; align-items:center; gap:8px;">
                Кол-во нажатий: <input type="number" name="dist_phone_count" value="1" min="1" max="1000" style="width:60px; padding:4px;">
            </div>
        </div>
        
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
            <label style="margin-bottom:0;"><input type="checkbox" name="chat"> Написать сообщение / Открыть чат</label>
            <div style="font-size:11px; color:var(--muted); display:flex; align-items:center; gap:8px;">
                Кол-во нажатий: <input type="number" name="dist_chat_count" value="1" min="1" max="1000" style="width:60px; padding:4px;">
            </div>
        </div>
    </div>
    
    <button type="submit" id="start-btn" style="width:100%; padding: 12px; font-size: 14px; margin-top: 8px;">▶ ЗАПУСТИТЬ ОРГАНИЧЕСКИЙ ТРАФИК</button>
  </form>
</div>

<div class="card">
  <h3>Объявления из базы</h3>
  <table>
    <thead><tr><th>ID / Заголовок</th><th>Действие (Потоки)</th><th>Опции</th><th>Запуск</th></tr></thead>
    <tbody>{ads_html}</tbody>
  </table>
</div>

<script>
async function startCustomBots() {
    const form = document.getElementById('custom-bots-form');
    const formData = new FormData(form);
    const btn = document.getElementById('start-btn');
    btn.innerText = 'ЗАПУСК...';
    btn.disabled = true;
    try {
        const r = await fetch('/bots/start_custom', { method: 'POST', body: formData });
        const res = await r.json();
        alert('Запущено задач: ' + res.task_ids.length);
    } catch(e) {
        alert('Ошибка при запуске');
    }
    btn.innerText = '▶ ЗАПУСТИТЬ ОРГАНИЧЕСКИЙ ТРАФИК';
    btn.disabled = false;
    updateTasks();
}

async function startBot(formId) {
    const form = document.getElementById(formId);
    const formData = new FormData(form);
    const btn = form.querySelector('button');
    btn.innerText = 'Запуск...';
    btn.disabled = true;
    try {
        const r = await fetch('/bots/start', { method: 'POST', body: formData });
        const res = await r.json();
        alert('Запущено потоков: ' + res.task_ids.length);
    } catch(e) {
        alert('Ошибка');
    }
    btn.innerText = '▶ Запустить';
    btn.disabled = false;
    updateTasks();
}

async function stopBot(tid) {
    if (!confirm('Остановить задачу ' + tid + '?')) return;
    try {
        await fetch('/bots/stop/' + tid, { method: 'POST' });
    } catch(e) {}
    updateTasks();
}

let currentFilter = 'all';
function setFilter(f) {
    currentFilter = f;
    const baseBtn = "color:var(--muted); border:1px solid var(--border); padding:4px 12px; font-size:11px;";
    const activeBtn = "background:var(--accent); color:#000; border:1px solid var(--accent); padding:4px 12px; font-size:11px;";
    
    document.getElementById('btn-filter-all').style = (f==='all' ? activeBtn : "background:var(--bg); " + baseBtn);
    document.getElementById('btn-filter-active').style = (f==='active' ? activeBtn : "background:var(--bg); " + baseBtn);
    document.getElementById('btn-filter-waiting').style = (f==='waiting' ? activeBtn : "background:var(--bg); " + baseBtn);
    updateTasks();
}

async function updateTasks() {
    try {
        const r = await fetch('/bots/status');
        const res = await r.json();
        const container = document.getElementById('tasks-container');
        
        let filteredTasks = {};
        for (const [tid, t] of Object.entries(res)) {
            let isWaiting = (t.status || "").toLowerCase().includes("ожидание");
            if (currentFilter === 'active' && isWaiting) continue;
            if (currentFilter === 'waiting' && !isWaiting) continue;
            filteredTasks[tid] = t;
        }

        const numTasks = Object.keys(filteredTasks).length;
        const totalTasks = Object.keys(res).length;
        
        const countSpanHeader = document.getElementById('active-tasks-count-header');
        if (countSpanHeader) countSpanHeader.innerText = totalTasks;
        
        if (numTasks === 0) {
            container.innerHTML = "Нет задач для отображения (возможно, они в очереди).";
        } else {
            let html = "";
            for (const [tid, t] of Object.entries(filteredTasks)) {
            let ipInfo = t.proxy_server ? t.proxy_server.replace('http://', '').replace('socks5://', '') : 'Прямой IP (195.245.96.252)';
            let accInfo = (!t.bot_account || t.bot_account === 'none' || t.bot_account === 'guest') ? 'Гость' : t.bot_account;
                let statusColor = (t.status || "").toLowerCase().includes("ошибк") ? "var(--danger)" : "var(--accent)";
                html += `<div class="task-card">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div style="font-size:10px; color:var(--muted); margin-bottom:4px;">ID: ${tid} | Акк: ${accInfo}</div>
                        <div style="display:flex; gap:4px;">
                            <a href="/live/${tid}" target="_blank" style="background:var(--blue); color:#fff; padding:2px 6px; border-radius:4px; font-size:10px; text-decoration:none;">🔴 Смотреть</a>
                            <button onclick="stopBot('${tid}')" style="background:#e74c3c; color:#fff; padding:2px 6px; border-radius:4px; font-size:10px; border:none; cursor:pointer;">⛔ Стоп</button>
                        </div>
                    </div>
                    <div>Статус: <b style="color:${statusColor}">${t.status}</b></div>
                <div style="font-size:10px; color:#ff9f43; margin-top:4px; font-weight:600;">IP: ${ipInfo}</div>
                <div style="margin-top:4px; font-size:10px; word-break:break-all; color:var(--blue);">${(t.url || "").substring(0, 40)}...</div>
            </div>`;
            }
            container.innerHTML = html;
        }
        
        // Update batch progress trackers
        document.querySelectorAll('.batch-live-progress').forEach(bar => {
            let linksStr = bar.getAttribute('data-links') || "";
            let linkAliases = linksStr.split(',').filter(Boolean).map(s => s.trim());
            
            let activeCount = 0;
            let waitingCount = 0;
            let finishedCount = 0;
            let totalCount = 0;
            
            for (const [tid, t] of Object.entries(res)) {
                let tUrl = String(t.url || "").trim();
                let isFinished = (t.status || "").toLowerCase().includes("завершено") || (t.status || "").toLowerCase().includes("ошибк");
                let isWaiting = (t.status || "").toLowerCase().includes("ожидание") || (t.status || "").toLowerCase().includes("очереди");
                
                if (tUrl) {
                    let isMatch = false;
                    for (let alias of linkAliases) {
                        if (tUrl.includes(alias) || alias.includes(tUrl)) {
                            isMatch = true;
                            break;
                        }
                    }
                    if (isMatch) {
                        totalCount++;
                        if (isFinished) {
                            finishedCount++;
                        } else if (isWaiting) {
                            waitingCount++;
                        } else {
                            activeCount++;
                        }
                    }
                }
            }
            
            if (totalCount > 0) {
                bar.style.display = 'block';
                let countEl = bar.querySelector('.batch-live-count');
                if (countEl) countEl.innerHTML = `<span style="color:#16c79a">${activeCount} акт.</span> <span style="color:var(--muted); font-weight:normal;">/ ${totalCount} задано</span>`;
            } else {
                bar.style.display = 'block';
                let seenUrls = Object.values(res).map(x => String(x.url).substring(0, 8)).join(",");
                let countEl = bar.querySelector('.batch-live-count');
                if (countEl) countEl.innerHTML = `<span style="color:red; font-size:9px;" title="Aliases: ${linkAliases.join(',')} | Seen: ${seenUrls}">0 (DEBUG: hover)</span>`;
            }
        });

        // Update single ad progress trackers
        document.querySelectorAll('.single-live-progress').forEach(bar => {
            let u = bar.getAttribute('data-url') || "";
            let uAliases = u.split(" ").filter(Boolean);
            
            let activeCount = 0;
            let waitingCount = 0;
            let finishedCount = 0;
            let totalCount = 0;
            
            for (const [tid, t] of Object.entries(res)) {
                let tUrl = String(t.url || "").trim();
                let isFinished = (t.status || "").toLowerCase().includes("завершено") || (t.status || "").toLowerCase().includes("ошибк");
                let isWaiting = (t.status || "").toLowerCase().includes("ожидание") || (t.status || "").toLowerCase().includes("очереди");
                
                if (tUrl) {
                    let isMatch = false;
                    for (let alias of uAliases) {
                        if (tUrl.includes(alias) || alias.includes(tUrl)) {
                            isMatch = true;
                            break;
                        }
                    }
                    if (isMatch) {
                        totalCount++;
                        if (isFinished) {
                            finishedCount++;
                        } else if (isWaiting) {
                            waitingCount++;
                        } else {
                            activeCount++;
                        }
                    }
                }
            }
            
            let countEl = bar.querySelector('.single-live-count');
            let fillEl = bar.querySelector('.bar-fill');
            
            if (countEl) {
                if (totalCount > 0) {
                    countEl.innerHTML = `<span style="color:#16c79a">${activeCount} активных</span> <span style="color:var(--muted); font-weight:normal;">/ ${totalCount} задано</span>`;
                } else {
                    let seenUrls = Object.values(res).map(x => String(x.url).substring(0, 8)).join(",");
                    countEl.innerHTML = `<span style="color:red; font-size:9px;" title="Aliases: ${uAliases.join(',')} | Seen: ${seenUrls}">0 (DEBUG: hover)</span>`;
                }
            }
            if (fillEl) {
                if (totalCount > 0) {
                    fillEl.style.width = '100%';
                    fillEl.style.opacity = activeCount > 0 ? '1' : '0.5';
                    fillEl.style.animation = activeCount > 0 ? 'progress-stripes 1s linear infinite' : 'none';
                } else {
                    fillEl.style.width = '0%';
                    fillEl.style.animation = 'none';
                }
            }
        });
        
    } catch(e) {
        document.getElementById('tasks-container').innerHTML += `<div style="color:red; font-size:10px;">Error in JS: ${e.message}</div>`;
    }
}
setInterval(updateTasks, 2000);
updateTasks();
</script>
"""

@app.get("/bots")
def bots_page():
    import glob
    import os
    account_opts = ""
    try:
        for p in glob.glob("accounts/*.json"):
            acc_name = os.path.basename(p).replace(".json", "")
            account_opts += f'<option value="{acc_name}">{acc_name}</option>'
    except:
        pass

    allrows = storage.latest_rows()
    ads_html = ""
    for r in allrows:
        url = r.get("url") or ""
        fid = f"form_{r['id']}"
        ads_html += f"""<tr>
            <td><a href="{url}" target="_blank" style="color:var(--accent);font-family:monospace">{r['id']}</a></td>
            <td>{r.get('title', '')[:50]}</td>
            <td>{r.get('city', '')}</td>
            <td>
                <form id="{fid}" onsubmit="event.preventDefault(); startBot('{fid}')" style="display:flex;gap:12px;align-items:center;">
                    <input type="hidden" name="url" value="{url}">
                    Кол-во: <input type="number" name="amount" value="1" min="1" max="10">
            </td>
            <td>
                    <label><input type="checkbox" name="scroll" checked> Скролл</label><br>
                    <label><input type="checkbox" name="phone"> Показать телефон</label><br>
                    <label><input type="checkbox" name="chat"> Открыть чат</label>
            </td>
            <td>
                    <button type="submit">▶ Запустить</button>
                </form>
            </td>
        </tr>"""
        
    batch_cards = ""
    try:
        import os
        import base64
        if os.path.exists("links.txt"):
            with open("links.txt", "r", encoding="utf-8") as f:
                content = f.read()
            
            import re
            current_city = "Свои ссылки"
            current_batch = ""
            current_batch_city = "Свои ссылки"
            current_links = []
            
            try:
                from bots.interaction import get_stats_for_date
                today_stats = get_stats_for_date()
            except:
                today_stats = {"urls": {}}
            
            def render_batch_card(city, batch, links):
                urls_str = "\n".join(links)
                b64 = base64.b64encode(urls_str.encode("utf-8")).decode("utf-8")
                links_html = "".join([f'<div style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-size:10px; color:var(--muted); margin-bottom:2px;"><a href="{u}" target="_blank" style="color:var(--blue); text-decoration:none;">{u}</a></div>' for u in links])
                
                success_count = 0
                urls_data = today_stats.get("urls", {})
                for u in links:
                    success_count += urls_data.get(u, {}).get("success", 0)
                    
                success_badge = f'<span style="background:rgba(22, 199, 154, 0.1); color:#16c79a; padding:2px 8px; border-radius:12px; font-size:11px; font-weight:700; border:1px solid rgba(22, 199, 154, 0.2); margin-left:12px;">✅ Успешно сегодня: {success_count}</span>'
                
                return f"""<form onsubmit="event.preventDefault(); startBatchBot(this)" class="task-card" style="margin-bottom:12px; padding:12px 16px;">
                    <input type="hidden" name="urls_b64" value="{b64}">
                    
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                        <div>
                            <span style="font-weight:bold; color:var(--accent); font-size:14px;">{city} — {batch}</span> 
                            <span style="color:var(--muted); font-size:12px; margin-left:6px;">({len(links)} ссылок)</span>
                            {success_badge}
                            <details style="margin-top:6px;">
                                <summary style="font-size:11px; color:var(--muted); cursor:pointer;">Показать ссылки</summary>
                                <div style="margin-top:4px; background:var(--bg); border:1px solid var(--border); padding:8px; border-radius:4px; max-height:100px; overflow-y:auto;">
                                    {links_html}
                                </div>
                            </details>
                            
                            <div class="batch-live-progress" data-links="{','.join(links)}" style="display:none; margin-top:12px; padding:8px; background:rgba(22, 199, 154, 0.05); border:1px solid rgba(22, 199, 154, 0.2); border-radius:4px;">
                                <div style="display:flex; align-items:center; gap:8px;">
                                    <div class="spinner" style="width:12px; height:12px; border:2px solid var(--accent); border-top-color:transparent; border-radius:50%; animation:spin 1s linear infinite;"></div>
                                    <div style="font-size:11px; color:var(--text);">В работе (или ожидании): <b class="batch-live-count" style="color:var(--accent);">0</b> задач</div>
                                </div>
                                <style>@keyframes spin {{ 100% {{ transform:rotate(360deg); }} }}</style>
                            </div>
                        </div>
                    </div>
                    
                    <div style="display:flex; justify-content:space-between; align-items:center; background:#15161c; border:1px solid var(--border); border-radius:8px; padding:6px 12px;">
                        
                        <div style="display:flex; align-items:center; gap:12px; flex-wrap:nowrap; overflow-x:auto;">
                            <div style="display:flex; align-items:center; gap:6px;">
                                <label style="font-size:10px; font-weight:700; color:var(--muted); text-transform:uppercase;">Ботов:</label>
                                <input type="number" name="amount" value="5" min="1" max="1000" style="width:45px; padding:2px 4px; height:24px; background:var(--bg); color:#fff; border:1px solid var(--border); border-radius:4px;">
                            </div>
                            
                            <div style="display:flex; align-items:center; gap:6px;">
                                <label style="font-size:10px; font-weight:700; color:var(--muted); text-transform:uppercase;">Режим:</label>
                                <select name="mode" style="width:90px; padding:2px 4px; height:24px; background:var(--bg); color:#fff; border:1px solid var(--border); border-radius:4px;" onchange="
                                    const w = this.parentElement.nextElementSibling;
                                    const h = w.querySelector('input[name=hours]');
                                    if(this.value === 'daily') {{ w.style.display = 'flex'; h.value = 24; }}
                                    else if(this.value === 'weekly') {{ w.style.display = 'flex'; h.value = 168; }}
                                    else {{ w.style.display = 'none'; }}
                                ">
                                    <option value="daily" selected>Суточный</option>
                                    <option value="fast">Сразу</option>
                                    <option value="weekly">Неделя</option>
                                </select>
                            </div>
                            
                            <div class="work-window-box" style="display:flex; align-items:center; gap:4px;">
                                <input type="time" name="work_start" value="08:00" style="width:65px; padding:2px; height:24px; background:var(--bg); color:#fff; border:1px solid var(--border); border-radius:4px; font-size:11px;">
                                <span style="color:var(--muted);">-</span>
                                <input type="time" name="work_end" value="23:00" style="width:65px; padding:2px; height:24px; background:var(--bg); color:#fff; border:1px solid var(--border); border-radius:4px; font-size:11px;">
                                <input type="hidden" name="hours" value="24">
                            </div>
                            
                            <div style="display:flex; align-items:center; gap:6px;">
                                <label style="font-size:10px; font-weight:700; color:var(--muted); text-transform:uppercase;">Аккаунт:</label>
                                <select name="bot_account" style="width:80px; padding:2px 4px; height:24px; background:var(--bg); color:#fff; border:1px solid var(--border); border-radius:4px;">
                                    <option value="guest">Гость</option>
                                    {account_opts}
                                </select>
                            </div>
                            
                            <div style="width:1px; height:16px; background:var(--border); margin:0 2px;"></div>
                            
                            <div style="display:flex; align-items:center; gap:10px;">
                                <label style="margin:0; font-size:11px; display:flex; align-items:center; gap:4px; cursor:pointer;"><input type="checkbox" name="scroll" checked style="margin:0; cursor:pointer;"> Скролл</label>
                                
                                <div style="display:flex; align-items:center; gap:4px;">
                                    <label style="margin:0; font-size:11px; display:flex; align-items:center; gap:4px; cursor:pointer;"><input type="checkbox" name="phone" style="margin:0; cursor:pointer;"> Тел</label>
                                    <input type="number" name="dist_phone_count" value="1" min="1" style="width:35px; padding:2px; height:22px; text-align:center; font-size:11px; background:var(--bg); color:#fff; border:1px solid var(--border); border-radius:4px;">
                                </div>
                                
                                <div style="display:flex; align-items:center; gap:4px;">
                                    <label style="margin:0; font-size:11px; display:flex; align-items:center; gap:4px; cursor:pointer;"><input type="checkbox" name="chat" style="margin:0; cursor:pointer;"> Чат</label>
                                    <input type="number" name="dist_chat_count" value="1" min="1" style="width:35px; padding:2px; height:22px; text-align:center; font-size:11px; background:var(--bg); color:#fff; border:1px solid var(--border); border-radius:4px;">
                                </div>
                            </div>
                        </div>
                        
                        <div style="margin-left:12px;">
                            <button type="submit" style="background:var(--accent); color:#000; height:28px; padding:0 16px; border-radius:4px; border:none; cursor:pointer; font-weight:bold; font-size:11px; white-space:nowrap; transition:0.2s opacity;" onmouseover="this.style.opacity='0.8'" onmouseout="this.style.opacity='1'">▶ ЗАПУСК</button>
                        </div>
                    </div>
                </form>"""
            
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("http"):
                    current_links.append(line)
                elif "," in line or line.isdigit():
                    # Parse comma separated numeric IDs
                    ids = [x.strip() for x in line.replace(" (снято)", "").split(",") if x.strip().isdigit()]
                    if ids:
                        current_links.extend(ids)
                elif "ПАЧКА" in line.upper() or "📦" in line or "🎯" in line or "MIX" in line.upper() or "ТЕСТ" in line.upper():
                    if current_batch and current_links:
                        batch_cards += render_batch_card(current_batch_city, current_batch, current_links)
                    current_batch = line.replace("📦", "").replace("🎯", "").replace("───────────────────────────────────────────", "").strip()
                    current_batch = current_batch.split("—")[0].strip() # Убираем хвост "— 5 ссылок"
                    current_links = []
                    
                    u_batch = current_batch.upper()
                    if "АЛМАТЫ" in u_batch or "ALMATY" in u_batch: current_city = "Алматы"
                    elif "КОСТАНАЙ" in u_batch: current_city = "Костанай"
                    elif "АСТАНА" in u_batch: current_city = "Астана"
                    elif "ПАВЛОДАР" in u_batch or "PAVLODAR" in u_batch: current_city = "Павлодар"
                    elif "ШЫМКЕНТ" in u_batch or "SHYMKENT" in u_batch: current_city = "Шымкент"
                    
                    current_batch_city = current_city
                elif "КОСТАНАЙ" in line.upper():
                    current_city = "Костанай"
                elif "Астана" in line or "АСТАНА" in line.upper():
                    current_city = "Астана"
                elif "АЛМАТЫ" in line.upper() or "ALMATY" in line.upper():
                    current_city = "Алматы"
                elif "ПАВЛОДАР" in line.upper() or "PAVLODAR" in line.upper():
                    current_city = "Павлодар"
                elif "ШЫМКЕНТ" in line.upper() or "SHYMKENT" in line.upper():
                    current_city = "Шымкент"
                    
            if current_batch and current_links:
                batch_cards += render_batch_card(current_batch_city, current_batch, current_links)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(e)
        
    return BOTS_HTML.replace("{ads_html}", ads_html).replace("{batch_cards}", batch_cards.replace("{{account_opts}}", account_opts))

@app.post("/bots/start")
def bots_start():
    import bots.interaction as bot
    url = request.form.get("url")
    amount = int(request.form.get("amount", 1))
    actions = {
        "scroll": request.form.get("scroll") == "on",
        "click_phone": request.form.get("phone") == "on",
        "click_chat": request.form.get("chat") == "on",
    }
    task_ids = bot.start_bot(url, actions, amount)
    return jsonify({"ok": True, "task_ids": task_ids})

@app.post("/bots/stop/<task_id>")
def bots_stop(task_id):
    import bots.interaction as bot
    if task_id in bot.active_tasks:
        bot.active_tasks[task_id]["cancel"] = True
    return jsonify({"ok": True})

@app.post("/bots/stop_all")
def bots_stop_all():
    import bots.interaction as bot
    # Очищаем очередь будущих задач
    with bot.global_queue_lock:
        bot.global_task_queue.clear()
    # Отменяем текущие активные задачи
    for task_id in list(bot.active_tasks.keys()):
        bot.active_tasks[task_id]["cancel"] = True
        bot.active_tasks[task_id]["status"] = "отменено"
    return jsonify({"ok": True, "message": "Все задачи остановлены"})


@app.post("/bots/start_custom")
def bots_start_custom():
    import bots.interaction as bot
    urls_raw = request.form.get("urls", "")
    amount = int(request.form.get("amount", 1))
    mode = request.form.get("mode", "fast")
    hours = int(request.form.get("hours", 24))
    
    actions = {
        "scroll": request.form.get("scroll") == "on",
        "click_phone": request.form.get("phone") == "on",
        "click_chat": request.form.get("chat") == "on",
        "bot_accounts": [request.form.get("bot_account")] if request.form.get("bot_account") not in ["guest", "none", None, ""] else [],
        "dist_hours": hours if mode in ["daily", "weekly"] else None,
        "dist_phone_count": int(request.form.get("dist_phone_count", 1)),
        "dist_chat_count": int(request.form.get("dist_chat_count", 1)),
        "work_start": request.form.get("work_start", "08:00"),
        "work_end": request.form.get("work_end", "23:00")
    }
    
    urls = [u.strip() for u in urls_raw.split("\n") if u.strip().startswith("http") or u.strip().isdigit()]
    
    all_task_ids = bot.start_bot_batch(urls, actions, amount)
    return jsonify({"ok": True, "task_ids": all_task_ids})

@app.get("/bots/status")
def bots_status():
    import bots.interaction as bot
    return jsonify(bot.get_status())
# --- BOTS UI ---

@app.get("/logs")
def logs_page():
    try:
        with open("bot_queue.log", "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        lines = ["Лог-файл пока пуст или не создан."]
        
    log_html = ""
    for line in reversed(lines):
        if not line.strip(): continue
        
        color = "var(--text)"
        if "РЕЗУЛЬТАТ" in line:
            if "success" in line:
                color = "var(--accent)"
            elif "warning" in line:
                color = "var(--yellow)"
            elif "error" in line:
                color = "var(--red)"
        elif "ОШИБКА" in line:
            color = "var(--red)"
        elif "Старт задачи" in line:
            color = "var(--blue)"
            
        log_html += f"<div style='color: {color}; margin-bottom: 4px; font-family: monospace;'>{line}</div>"
        
    page = PAGE.format(n="Логи", accs="", theme=THEME) + f'''
    <h2>📜 Логи выполнения задач</h2>
    <div style="background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 16px; max-height: 70vh; overflow-y: auto;">
        {log_html}
    </div>

    <script>
        document.querySelector(".nav-links a.active")?.classList.remove("active");
        document.querySelectorAll(".nav-links a").forEach(a => {{
            if(a.href.endsWith("/logs")) a.classList.add("active");
        }});
        setInterval(() => window.location.reload(), 10000);
    </script>
    '''
    return page

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "8000")))
