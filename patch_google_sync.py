import codecs

content = codecs.open('web.py', 'r', 'utf-8', errors='replace').read()

# 1. Добавляем endpoint /whatsapp/sync_google
endpoint_code = """
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
        for row in values:
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
                        "reason": ""
                    })
                    existing_urls.add(url)
                    added += 1
                    
        save_whatsapp_groups(groups)
        
        # Сохраняем последнюю ссылку чтобы не вводить каждый раз
        config_data = load_whatsapp_config()
        config_data["last_sheet_url"] = sheet_url
        with open("config_whatsapp.json", "w", encoding="utf-8") as f:
            import json
            json.dump(config_data, f, ensure_ascii=False, indent=4)
            
    except Exception as e:
        return f"Ошибка при синхронизации с Google: {e}", 500
        
    return redirect("/whatsapp")

@app.post("/whatsapp/save_templates")"""

if "/whatsapp/sync_google" not in content:
    content = content.replace('@app.post("/whatsapp/save_templates")', endpoint_code)


# 2. Обновляем UI в whatsapp_page (добавляем форму для Google Sheets)
ui_code = """    <div style="background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-top: 24px;">
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
        </div>"""

old_ui_start = """    <div style="background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-top: 24px;">
        <h3 style="margin-bottom: 16px; color: var(--accent); font-size: 16px;">📂 База групп для рассылки (CSV)</h3>
        
        <form action="/whatsapp/upload_csv" method="POST" enctype="multipart/form-data" style="margin-bottom: 20px; display: flex; gap: 12px; align-items: center;">
            <input type="file" name="csv_file" accept=".csv,.txt" required style="padding: 8px; background: var(--bg); border: 1px solid var(--border); border-radius: 6px; color: #fff; flex: 1;">
            <button type="submit" style="padding: 10px 16px; font-size: 13px; border-radius: 6px; background: var(--blue); color: #fff; font-weight: bold; border: none; cursor: pointer; transition: 0.2s;">📥 Загрузить CSV</button>
            <a href="/whatsapp/clear_csv" style="padding: 10px 16px; font-size: 13px; border-radius: 6px; background: var(--danger); color: #fff; font-weight: bold; border: none; cursor: pointer; text-decoration: none; transition: 0.2s;" onclick="return confirm('Очистить список?')">🗑 Очистить</a>
        </form>"""

if old_ui_start in content:
    content = content.replace(old_ui_start, ui_code)

with codecs.open('web.py', 'w', 'utf-8') as f:
    f.write(content)
