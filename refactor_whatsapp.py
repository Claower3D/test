import codecs

content = codecs.open('web.py', 'r', 'utf-8', errors='replace').read()

# We need to find @app.get("/autoreply")
start_idx = content.find('@app.get("/autoreply")')
end_idx = content.find('@app.post("/whatsapp/upload_csv")')

if start_idx != -1 and end_idx != -1:
    new_code = """
import subprocess

@app.post("/whatsapp_send")
def whatsapp_send_now():
    # Запускаем скрипт рассылки в фоне
    try:
        subprocess.Popen(["python", "whatsapp_sender.py"], shell=False)
        return jsonify({"status": "запущено"})
    except Exception as e:
        return jsonify({"status": "ошибка", "error": str(e)})

@app.get("/whatsapp")
def whatsapp_page():
    config_data = load_whatsapp_config()
    
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
        
        <!-- Левая колонка: настройки -->
        <div style="background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 20px;">
            <h3 style="margin-bottom: 16px; color: var(--accent); font-size: 16px;">📝 Текст рассылки</h3>
            <form action="/whatsapp/save" method="POST">
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: bold; font-size: 13px;">Текст сообщения (отправляется вместе с видео):</label>
                    <textarea name="text_template" required style="width: 100%; min-height: 120px; box-sizing: border-box; padding: 10px 12px; background: var(--bg); border: 1px solid var(--border); color: #fff; border-radius: 6px; font-family: inherit; font-size: 13px; line-height: 1.5; resize: vertical;">{config_data.get("text_template", "")}</textarea>
                </div>
                
                <button type="submit" style="width: 100%; padding: 12px; font-size: 14px; border-radius: 6px; background: var(--accent); color: #000; font-weight: 700; border: none; cursor: pointer; transition: 0.2s;">💾 Сохранить текст</button>
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
                    <button onclick="runSender()" style="flex: 1; min-width: 150px; padding: 14px; font-size: 14px; border-radius: 6px; background: var(--danger); color: #fff; font-weight: bold; border: none; cursor: pointer; transition: 0.2s;">🚀 Запустить рассылку в браузере</button>
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
                        // Обновляем страницу каждые 5 сек чтобы видеть как меняются статусы
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
    # Using utf-8 writing
    with codecs.open('web.py', 'w', 'utf-8') as f:
        f.write(content[:start_idx] + new_code + content[end_idx:])
