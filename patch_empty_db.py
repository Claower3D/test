import re

with open("web.py", "r", encoding="utf-8") as f:
    content = f.read()

# I will update bots_page to also include inactive ads or just check all adverts so the user can test
replacement = """@app.get("/bots")
def bots_page():
    # Retrieve all adverts (even if they are not active or have no stats yet for testing)
    c = storage.conn()
    allrows = c.execute("SELECT * FROM adverts").fetchall()
    c.close()
    
    ads_html = ""
    for r in allrows:
        r = dict(r)
        url = r.get("url") or f"https://olx.kz/obyavlenie/{r['id']}"
        fid = f"form_{r['id']}"
        ads_html += f'''<tr>
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
        </tr>'''
        
    if not ads_html:
        # User has NO adverts in the DB. Show a custom input form!
        ads_html = '''<tr>
            <td colspan="6" style="text-align:center; padding: 20px;">
                <p style="color:var(--muted); margin-bottom: 10px;">В базе данных нет сохраненных объявлений.</p>
                <form id="custom_form" onsubmit="event.preventDefault(); startBot('custom_form')" style="display:flex;gap:12px;align-items:center;justify-content:center;">
                    <input type="text" name="url" placeholder="https://www.olx.kz/d/obyavlenie/..." style="padding: 6px; border-radius: 4px; border: 1px solid var(--border); background: var(--bg); color: #fff; width: 250px;" required>
                    Кол-во: <input type="number" name="amount" value="1" min="1" max="10">
                    <div style="text-align:left; font-size: 11px;">
                        <label><input type="checkbox" name="scroll" checked> Скролл</label><br>
                        <label><input type="checkbox" name="phone"> Показать телефон</label><br>
                        <label><input type="checkbox" name="chat"> Открыть чат</label>
                    </div>
                    <button type="submit">▶ Запустить (Своя ссылка)</button>
                </form>
            </td>
        </tr>'''
        
    return BOTS_HTML.replace('{ads_html}', ads_html)"""

content = re.sub(r"@app\.get\(\"/bots\"\)\ndef bots_page\(\):[\s\S]*?return BOTS_HTML\.replace\('\{ads_html\}', ads_html\)", replacement, content)

with open("web.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated bots_page to show custom URL input if DB is empty")
