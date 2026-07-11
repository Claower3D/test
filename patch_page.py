import re

with open("web.py", "r", encoding="utf-8") as f:
    content = f.read()

# I will replace the PAGE string in web.py
old_page_str = """PAGE = \"\"\"<!doctype html><meta charset=utf-8><title>OLX бот — Главная панель</title>
{theme}
<h2>🏠 Главная панель</h2>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin:14px 0">
<a href="/stats" style="text-decoration:none"><button class=btnred>📊 Вчерашняя статистика</button></a>
<a href="/weekly" style="text-decoration:none"><button class=btnred>📅 Еженедельная статистика</button></a>
<a href="/dashboard" style="text-decoration:none"><button style="background:#3a86ff;border-color:#3a86ff;color:#fff">📈 Дашборд</button></a>
<a href="/create" style="text-decoration:none"><button class=btngreen>➕ Создать объявление</button></a>
<a href="/bots" style="text-decoration:none"><button style="background:#3a86ff;border-color:#3a86ff;color:#fff">🤖 Боты</button></a>
<a href="/promo" style="text-decoration:none"><button style="background:#f5c542;border-color:#f5c542;color:#1a1505">🚀 ABDU</button></a>
</div>
<div class=card><b>Подключённые аккаунты ({n})</b>{accs}</div>
<div class=card><b>Добавить аккаунт</b><p class=muted style="font-size:14px">Залогинься в OLX под нужным аккаунтом в этом браузере, впиши метку и нажми «Авторизовать».</p>
<form action=/login method=get>
<input name=account placeholder="метка, напр. account_2" required>
<button class=btnred>Авторизовать в OLX</button></form></div>
<div class=card><button id=runBtn style="width:100%" onclick="startRun()">▶ Запустить сбор сейчас</button></div>
\"\"\""""

new_page_str = """PAGE = \"\"\"<!doctype html><meta charset=utf-8><title>OLX бот — Главная панель</title>
{theme}
<div class='nav-links'>
    <a href='/' class='active'>Главная</a>
    <a href='/stats'>Вчерашняя</a>
    <a href='/weekly'>Еженедельная</a>
    <a href='/dashboard'>Дашборд</a>
    <a href='/bots'>Боты</a>
</div>

<h2>🏠 Управление аккаунтами OLX</h2>
<div style="display:flex;gap:10px;flex-wrap:wrap;margin:14px 0 24px 0">
    <a href="/create" style="text-decoration:none"><button style="background:var(--accent);color:#000">➕ Создать объявление</button></a>
    <a href="/promo" style="text-decoration:none"><button style="background:var(--yellow);color:#000">🚀 Промо ABDU</button></a>
</div>

<div class="kpi" style="grid-template-columns: 1fr; max-width: 600px;">
    <div>
        <b style="font-size: 18px; margin-bottom: 8px;">➕ Добавить новый OLX аккаунт</b>
        <p class=muted style="font-size:13px; line-height:1.5;">Залогинься в OLX в текущем браузере (в соседней вкладке), придумай понятную метку для аккаунта и нажми «Авторизовать». Система привяжет его к аналитике и ботам.</p>
        <form action=/login method=get style="display:flex; gap:10px;">
            <input name=account placeholder="Например: Магазин 1" required style="flex:1;">
            <button style="background:var(--accent);color:#000;">Авторизовать в OLX</button>
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
\"\"\""""

content = content.replace(old_page_str, new_page_str)

with open("web.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Updated PAGE theme and made adding accounts more prominent")
