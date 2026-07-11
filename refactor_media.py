import codecs
import os

if not os.path.exists("media"):
    os.makedirs("media")

content = codecs.open('web.py', 'r', 'utf-8', errors='replace').read()

start_idx = content.find('@app.post("/whatsapp/save_templates")')
end_idx = content.find('@app.post("/whatsapp/upload_csv")')

if start_idx != -1 and end_idx != -1:
    new_code = """@app.post("/whatsapp/save_templates")
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
            media_html = f\"\"\"
            <div style="margin-top: 10px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 6px; display: flex; align-items: center; justify-content: space-between;">
                <div style="font-size: 12px; color: var(--blue);">📎 Прикреплен файл: <b>{os.path.basename(media_path)}</b></div>
                <button type="submit" name="action" value="delmedia_{i}" style="background: none; border: none; color: var(--danger); cursor: pointer; font-size: 12px; font-weight: bold;">Удалить медиа</button>
            </div>
            \"\"\"
            
        templates_html += f\"\"\"
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
        \"\"\"

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
            
        groups_rows += f\"\"\"
        <tr style="background: {bg_color}; border-bottom: 1px solid var(--border);">
            <td style="padding: 10px;">{g.get('name', 'Без названия')}</td>
            <td style="padding: 10px;"><a href="{g.get('url', '')}" target="_blank" style="color:var(--blue); text-decoration:none;">{g.get('url', '')}</a></td>
            <td style="padding: 10px; font-weight: bold;">{st_text}</td>
            <td style="padding: 10px; color: var(--muted); font-size: 12px;">{g.get('reason', '')}</td>
        </tr>
        \"\"\"

    custom_html = f\"\"\"
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
                <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                    <button onclick="runSender()" style="flex: 1; min-width: 150px; padding: 14px; font-size: 14px; border-radius: 6px; background: var(--danger); color: #fff; font-weight: bold; border: none; cursor: pointer; transition: 0.2s;">🚀 Запустить рассылку</button>
                </div>
                <div id="run-status" style="margin-top: 16px; padding: 12px; border-radius: 6px; background: rgba(255, 255, 255, 0.02); border: 1px dashed var(--border); text-align: center; font-size: 13px; color: var(--muted); font-weight: bold; display: none;">
                    Открывается браузер...
                </div>
            </div>
        </div>
    </div>
    
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
                    {groups_rows if groups_rows else '<tr><td colspan="4" style="padding: 16px; text-align: center; color: var(--muted);">Нет данных. Сохраните таблицу Excel как CSV и загрузите её.</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>

    <script>
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
    \"\"\"
    
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

"""
    with codecs.open('web.py', 'w', 'utf-8') as f:
        f.write(content[:start_idx] + new_code + content[end_idx:])
