import re

with open("web.py", "r", encoding="utf-8") as f:
    content = f.read()

if "from flask import send_file" not in content:
    content = content.replace("from flask import Flask,", "from flask import Flask, send_file,")
    
live_code = """
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
    <img id="screen" src="/live_img/{task_id}?t=0" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'400\\' height=\\'300\\'><rect width=\\'400\\' height=\\'300\\' fill=\\'%231c1d25\\'/><text x=\\'50%\\' y=\\'50%\\' fill=\\'%238b8b99\\' dominant-baseline=\\'middle\\' text-anchor=\\'middle\\' font-family=\\'sans-serif\\'>Ожидание изображения...</text></svg>'" />
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
"""

if "@app.get(\"/live/<task_id>\")" not in content:
    content = content.replace("# --- BOTS UI ---", live_code + "\n# --- BOTS UI ---", 1)

# Modify updateTasks in web.py to add the "Смотреть" button
old_js = """html += `<div style="padding:8px; border:1px solid var(--border); border-radius:6px; margin-bottom:8px;">
                <b>ID:</b> ${tid} | <b>Статус:</b> <span style="color:var(--accent)">${t.status}</span>
            </div>`;"""
new_js = """html += `<div style="padding:8px; border:1px solid var(--border); border-radius:6px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
                <div><b>ID:</b> ${tid} | <b>Статус:</b> <span style="color:var(--accent)">${t.status}</span></div>
                <a href="/live/${tid}" target="_blank" style="background:var(--blue); color:#fff; padding:4px 8px; border-radius:4px; font-size:11px; text-decoration:none;">🔴 Смотреть</a>
            </div>`;"""

content = content.replace(old_js, new_js)

with open("web.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Added Live UI")
