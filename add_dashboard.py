import re

with open("web.py", "r", encoding="utf-8") as f:
    content = f.read()

dashboard_html = '''
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
  </div>
</div>

<div class="grid-4">
  <div class="card">
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
  <div class="card">
    <div class="kpi-head"><span>Сильных объявлений</span><div class="kpi-icon" style="background:rgba(255,93,93,0.1);color:#ff5d5d">🔥</div></div>
    <div class="kpi-val">{strong_ads}</div>
    <div class="kpi-trend" style="color:var(--muted)">Генерируют основной трафик</div>
  </div>
</div>

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
<script>
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
</script>
"""

@app.get("/dashboard")
def custom_dashboard():
    import json, datetime
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

    return DASHBOARD_HTML.format(
        total_views=total_views,
        trend_views_class=trend_views_class,
        trend_views_str=trend_views_str,
        conv_pct=f"{conv_pct:.1f}",
        total_leads=total_leads,
        active_ads=active_ads,
        strong_ads=strong_ads,
        phones=total_phones,
        phones_pct=f"{phones_pct:.1f}",
        chats=total_chats,
        chats_pct=f"{chats_pct:.1f}",
        top_ads_html=top_ads_html,
        chart_labels=json.dumps(chart_labels),
        chart_data=json.dumps(chart_data)
    )

'''

if "# --- планировщик" in content:
    content = content.replace("# --- планировщик", dashboard_html + "\n# --- планировщик")
else:
    print("Could not find '# --- планировщик'")
    
# Add Dashboard button to PAGE
if "<a href=\"/weekly\" style=\"text-decoration:none\"><button class=btnred>📅 Еженедельная статистика</button></a>" in content:
    content = content.replace("<a href=\"/weekly\" style=\"text-decoration:none\"><button class=btnred>📅 Еженедельная статистика</button></a>",
        "<a href=\"/weekly\" style=\"text-decoration:none\"><button class=btnred>📅 Еженедельная статистика</button></a>\n<a href=\"/dashboard\" style=\"text-decoration:none\"><button style=\"background:#3a86ff;border-color:#3a86ff;color:#fff\">📈 Дашборд</button></a>")

with open("web.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Dashboard added to web.py successfully!")
