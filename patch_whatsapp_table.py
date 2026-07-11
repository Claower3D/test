import codecs
import re

content = codecs.open('web.py', 'r', 'utf-8').read()

if "def load_whatsapp_groups" not in content:
    helpers = """
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
"""
    content = content.replace("def update_scheduler_jobs():", helpers + "\ndef update_scheduler_jobs():")

if "whatsapp_groups.json" not in content and "load_whatsapp_groups()" not in content:
    pass

html_groups = """
    groups_data = load_whatsapp_groups()
    groups_rows = ""
    for g in groups_data:
        bg_color = "rgba(255,255,255,0.02)"
        st_text = "⏳ Ожидает"
        if g.get('status') == 'success':
            bg_color = "rgba(0, 255, 0, 0.1)"
            st_text = "✅ Успешно"
        elif g.get('status') == 'error':
            bg_color = "rgba(255, 0, 0, 0.1)"
            st_text = "❌ Ошибка"
            
        groups_rows += f\"\"\"
        <tr style="background: {bg_color}; border-bottom: 1px solid var(--border);">
            <td style="padding: 10px;">{g.get('name', 'Без названия')}</td>
            <td style="padding: 10px;"><a href="{g.get('url', '')}" target="_blank" style="color:var(--blue); text-decoration:none;">{g.get('url', '')}</a></td>
            <td style="padding: 10px; font-weight: bold;">{st_text}</td>
            <td style="padding: 10px; color: var(--muted); font-size: 12px;">{g.get('reason', '')}</td>
        </tr>
        \"\"\"
        
    custom_html += f\"\"\"
    <div style="background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-top: 24px;">
        <h3 style="margin-bottom: 16px; color: var(--accent); font-size: 16px;">📂 База групп для рассылки (CSV)</h3>
        
        <form action="/whatsapp/upload_csv" method="POST" enctype="multipart/form-data" style="margin-bottom: 20px; display: flex; gap: 12px; align-items: center;">
            <input type="file" name="csv_file" accept=".csv,.txt" required style="padding: 8px; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; color: #fff; flex: 1;">
            <button type="submit" style="padding: 10px 16px; font-size: 13px; border-radius: 6px; background: var(--blue); color: #fff; font-weight: bold; border: none; cursor: pointer; transition: 0.2s;">📥 Загрузить CSV</button>
            <a href="/whatsapp/clear_csv" style="padding: 10px 16px; font-size: 13px; border-radius: 6px; background: var(--danger); color: #fff; font-weight: bold; border: none; cursor: pointer; text-decoration: none; transition: 0.2s;" onclick="return confirm('Очистить список?')">🗑 Очистить</a>
        </form>
        
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
                    {groups_rows if groups_rows else '<tr><td colspan="4" style="padding: 16px; text-align: center; color: var(--muted);">Нет данных. Сохраните таблицу Excel как CSV (разделитель запятая или точка с запятой) и загрузите её.</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>
    \"\"\"
"""
if "📂 База групп для рассылки (CSV)" not in content:
    content = content.replace("    <script>", html_groups + "\n    <script>")

endpoints = """
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
        
        # Определяем разделитель
        delimiter = ','
        if lines and ';' in lines[0] and lines[0].count(';') > lines[0].count(','):
            delimiter = ';'
            
        reader = csv.reader(lines, delimiter=delimiter)
        groups = []
        for i, row in enumerate(reader):
            if i == 0 or len(row) < 3:
                continue # Заголовок или пустая строка
            
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
"""
if "@app.post(\"/whatsapp/upload_csv\")" not in content:
    content = content.replace("@app.post(\"/whatsapp/save\")", endpoints + "\n@app.post(\"/whatsapp/save\")")

with codecs.open('web.py', 'w', 'utf-8') as f:
    f.write(content)
