import re

with open("web.py", "r", encoding="utf-8") as f:
    content = f.read()

# Remove all occurrences of BOTS_HTML
while "# --- BOTS UI ---" in content:
    # Find the block starting with # --- BOTS UI --- and ending with the second # --- BOTS UI ---
    start = content.find("# --- BOTS UI ---")
    end = content.find("# --- BOTS UI ---", start + 1)
    if end != -1:
        # Include the marker in the removal
        content = content[:start] + content[end + len("# --- BOTS UI ---"):]
    else:
        # If there's only one marker but something is messed up, remove from start to end of file?
        # Actually it's better to just regex it out
        break

# Now append it once correctly before if __name__ == "__main__":

bot_code = '''
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
button { background: var(--accent); color: #000; border: none; padding: 6px 12px; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 12px; }
button:hover { opacity: 0.9; }
input[type=number] { background: var(--bg); border: 1px solid var(--border); color: #fff; padding: 4px; border-radius: 4px; width: 60px; }
input[type=checkbox] { accent-color: var(--accent); }
</style>
<div class="header">
  <div class="title-area">
    <h1>🤖 Управление ботами</h1>
    <div class="subtitle">Имитация просмотров и активности на объявлениях (скролл, клики на телефон и чат)</div>
  </div>
  <div class="nav-pills">
    <a href="/">Главная</a>
    <a href="/stats">Вчерашняя</a>
    <a href="/weekly">Еженедельная</a>
    <a href="/dashboard">Дашборд</a>
    <a href="/bots" class="active">🤖 Боты</a>
  </div>
</div>

<div class="card">
  <h3>Активные задачи</h3>
  <div id="tasks-container" style="margin-top:12px;font-size:12px;color:var(--muted)">Нет запущенных ботов.</div>
</div>

<div class="card">
  <h3>Ваши объявления</h3>
  <table>
    <thead><tr><th>ID</th><th>Заголовок</th><th>Город</th><th>Действие (Потоки)</th><th>Опции</th><th>Запуск</th></tr></thead>
    <tbody>{ads_html}</tbody>
  </table>
</div>
<script>
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

async function updateTasks() {
    try {
        const r = await fetch('/bots/status');
        const res = await r.json();
        const container = document.getElementById('tasks-container');
        if (Object.keys(res).length === 0) {
            container.innerHTML = "Нет запущенных ботов.";
            return;
        }
        let html = "";
        for (const [tid, t] of Object.entries(res)) {
            html += `<div style="padding:8px; border:1px solid var(--border); border-radius:6px; margin-bottom:8px;">
                <b>ID:</b> ${tid} | <b>Статус:</b> <span style="color:var(--accent)">${t.status}</span>
            </div>`;
        }
        container.innerHTML = html;
    } catch(e) {}
}
setInterval(updateTasks, 2000);
updateTasks();
</script>
"""

@app.get("/bots")
def bots_page():
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
        
    return BOTS_HTML.format(ads_html=ads_html)

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

@app.get("/bots/status")
def bots_status():
    import bots.interaction as bot
    return jsonify(bot.get_status())
# --- BOTS UI ---
'''

content = content.replace('if __name__ == "__main__":', bot_code + '\nif __name__ == "__main__":')

with open("web.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Cleaned up duplicates and injected UI")
