import codecs

content = codecs.open('web.py', 'r', 'utf-8').read()

start_idx = content.find("def whatsapp_page():")
end_idx = content.find("@app.post(\"/whatsapp/save\")")

new_func = """def whatsapp_page():
    config_data = load_whatsapp_config()
    import autoreply
    last_run = getattr(autoreply, "LAST", {"status": "нет данных"})
    
    enabled_val = config_data.get("enabled", "0")
    status_text = '🟢 РАБОТАЕТ ПО РАСПИСАНИЮ' if enabled_val == '1' else '⚪ ВЫКЛЮЧЕН'
    status_color = 'var(--accent)' if enabled_val == '1' else 'var(--muted)'
    
    error_html = ""
    if 'error' in last_run:
        error_html = f"<div style='margin-bottom: 6px; color: var(--danger);'>Ошибка: {last_run.get('error')}</div>"
        
    finished_html = ""
    if 'finished_at' in last_run:
        finished_html = f"<div style='margin-top: 8px; font-size: 11px; color: var(--muted);'>Завершено в: {last_run.get('finished_at')}</div>"

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

    custom_html = f\"\"\"
    <h2>💬 WhatsApp Автоответчик</h2>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 24px; margin-top: 20px;">
        <!-- Левая колонка: настройки -->
        <div style="background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 20px;">
            <h3 style="margin-bottom: 16px; color: var(--accent); font-size: 16px;">⚙️ Параметры автоответчика</h3>
            <form action="/whatsapp/save" method="POST">
                <div style="margin-bottom: 16px;">
                    <label style="display: flex; align-items: center; gap: 10px; font-weight: bold; font-size: 14px; margin-bottom: 8px;">
                        <input type="checkbox" name="enabled" value="1" {"checked" if enabled_val == "1" else ""} style="width: 18px; height: 18px; cursor: pointer; accent-color: var(--accent);">
                        Включить автоответчик по расписанию
                    </label>
                    <small style="color: var(--muted); display: block; margin-top: 4px; line-height: 1.4;">Если включено, бот будет автоматически проверять новые сообщения с заданным интервалом.</small>
                </div>
                
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: bold; font-size: 13px;">Интервал проверки (в минутах):</label>
                    <input type="number" name="interval" value="{config_data.get("interval", "15")}" min="1" max="1440" required style="width: 100%; box-sizing: border-box; padding: 10px 12px; background: var(--bg); border: 1px solid var(--border); color: #fff; border-radius: 6px; font-size: 14px;">
                </div>
                
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: bold; font-size: 13px;">Номер WhatsApp (куда переводить):</label>
                    <input type="text" name="wa_number" value="{config_data.get("wa_number", "")}" placeholder="Например: 77071234567" style="width: 100%; box-sizing: border-box; padding: 10px 12px; background: var(--bg); border: 1px solid var(--border); color: #fff; border-radius: 6px; font-size: 14px;">
                    <small style="color: var(--muted); display: block; margin-top: 4px; line-height: 1.4;">Введите номер в международном формате (только цифры). Если оставить пустым, бот перенаправит на номер аккаунта, с которого пишется ответ.</small>
                </div>
                
                <div style="margin-bottom: 16px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: bold; font-size: 13px;">Дата старта (отвечать на сообщения новее чем):</label>
                    <input type="text" name="since_date" value="{config_data.get("since_date", "")}" placeholder="ГГГГ-ММ-ДДTЧЧ:ММ:СС (например: 2026-07-01T00:00:00)" style="width: 100%; box-sizing: border-box; padding: 10px 12px; background: var(--bg); border: 1px solid var(--border); color: #fff; border-radius: 6px; font-size: 14px;">
                    <small style="color: var(--muted); display: block; margin-top: 4px; line-height: 1.4;">Оставьте пустым, чтобы отвечать на все накопившиеся необработанные сообщения.</small>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 6px; font-weight: bold; font-size: 13px;">Текст приветственного сообщения:</label>
                    <textarea name="text_template" required style="width: 100%; min-height: 120px; box-sizing: border-box; padding: 10px 12px; background: var(--bg); border: 1px solid var(--border); color: #fff; border-radius: 6px; font-family: inherit; font-size: 13px; line-height: 1.5; resize: vertical;">{config_data.get("text_template", "")}</textarea>
                    <small style="color: var(--muted); display: block; margin-top: 4px; line-height: 1.4;">Используйте переменные <b>{{wa}}</b> (номер) и <b>{{wame}}</b> (ссылка wa.me).</small>
                </div>
                
                <button type="submit" style="width: 100%; padding: 12px; font-size: 14px; border-radius: 6px; background: var(--accent); color: #000; font-weight: 700; border: none; cursor: pointer; transition: 0.2s;">💾 Сохранить изменения</button>
            </form>
        </div>
        
        <!-- Правая колонка: статус и запуск -->
        <div style="background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 20px; display: flex; flex-direction: column; justify-content: space-between; gap: 24px;">
            <div>
                <h3 style="margin-bottom: 16px; color: var(--accent); font-size: 16px;">📊 Текущий статус работы</h3>
                
                <div style="margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between;">
                    <span style="font-size: 14px; color: var(--muted);">Режим планировщика:</span>
                    <span style="font-size: 14px; font-weight: bold; padding: 4px 8px; border-radius: 6px; background: rgba(255,255,255,0.05); color: {status_color};">
                        {status_text}
                    </span>
                </div>
                
                <div style="background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 16px; font-family: monospace; font-size: 13px; line-height: 1.6;">
                    <div style="font-weight: bold; border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 8px; color: var(--blue); font-size: 14px;">Результаты последнего запуска:</div>
                    <div style="margin-bottom: 6px;">Статус: <span style="color:#fff; font-weight:bold;">{last_run.get('status', 'нет данных')}</span></div>
                    <div style="margin-bottom: 6px;">Режим: <span style="color:#fff;">{'Тестовый (сухой)' if last_run.get('dry') else 'Реальная отправка'}</span></div>
                    <div style="margin-bottom: 6px;">Проверено диалогов: <span style="color:#fff; font-weight:bold;">{last_run.get('scanned', 0)}</span></div>
                    <div style="margin-bottom: 6px;">Будет отправлено: <span style="color:#fff; font-weight:bold;">{last_run.get('would', 0)}</span></div>
                    <div style="margin-bottom: 6px;">Реально отправлено: <span style="color:#fff; font-weight:bold;">{last_run.get('sent', 0)}</span></div>
                    {error_html}
                    {finished_html}
                </div>
            </div>
            
            <div>
                <h3 style="margin-bottom: 16px; color: var(--accent); font-size: 16px;">🚀 Запустить вручную прямо сейчас</h3>
                <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                    <button onclick="runAutoreply(0)" style="flex: 1; min-width: 150px; padding: 12px; font-size: 13px; border-radius: 6px; background: var(--yellow); color: #000; font-weight: bold; border: none; cursor: pointer; transition: 0.2s;">🔍 Тестовый прогон</button>
                    <button onclick="runAutoreply(1)" style="flex: 1; min-width: 150px; padding: 12px; font-size: 13px; border-radius: 6px; background: var(--danger); color: #fff; font-weight: bold; border: none; cursor: pointer; transition: 0.2s;">🚀 Реальная отправка</button>
                </div>
                <div id="run-status" style="margin-top: 16px; padding: 12px; border-radius: 6px; background: rgba(255, 255, 255, 0.02); border: 1px dashed var(--border); text-align: center; font-size: 13px; color: var(--muted); font-weight: bold; display: none;">
                    Запуск процесса...
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
                    {groups_rows if groups_rows else '<tr><td colspan="4" style="padding: 16px; text-align: center; color: var(--muted);">Нет данных. Сохраните таблицу Excel как CSV (разделитель запятая или точка с запятой) и загрузите её.</td></tr>'}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function runAutoreply(send) {{
            const statusDiv = document.getElementById("run-status");
            statusDiv.style.display = "block";
            statusDiv.style.borderColor = "var(--blue)";
            statusDiv.style.color = "var(--blue)";
            statusDiv.innerText = "Запуск автоответчика в фоне... Подождите...";
            
            fetch("/autoreply?send=" + send, {{ method: "POST" }})
                .then(res => res.json())
                .then(data => {{
                    statusDiv.innerText = "Процесс запущен! Проверяем результаты...";
                    statusDiv.style.color = "var(--accent)";
                    statusDiv.style.borderColor = "var(--accent)";
                    
                    let attempts = 0;
                    const intervalId = setInterval(() => {{
                        attempts++;
                        fetch("/autoreply/result")
                            .then(r => r.json())
                            .then(result => {{
                                if (result.status === "готово" || result.status.includes("готово") || result.status === "ошибка" || attempts > 30) {{
                                    clearInterval(intervalId);
                                    statusDiv.innerText = `Завершено! Статус: ${{result.status}}. Проверено: ${{result.scanned}}, Отправлено: ${{result.sent}} (будет: ${{result.would}})`;
                                    if (result.status === "ошибка") {{
                                        statusDiv.style.color = "var(--danger)";
                                        statusDiv.style.borderColor = "var(--danger)";
                                        statusDiv.innerText += `. Ошибка: ${{result.error || ''}}`;
                                    }} else {{
                                        statusDiv.style.color = "var(--accent)";
                                        statusDiv.style.borderColor = "var(--accent)";
                                    }}
                                    setTimeout(() => window.location.reload(), 3000);
                                }} else {{
                                    statusDiv.innerText = `В процессе... (проверено ${{result.scanned || 0}} диалогов)`;
                                }}
                            }});
                    }}, 1500);
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
        "<title>WhatsApp бот автоответчик</title>"
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

content = content[:start_idx] + new_func + content[end_idx:]

with codecs.open('web.py', 'w', 'utf-8') as f:
    f.write(content)
