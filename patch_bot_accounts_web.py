import os, json, re

os.makedirs("bot_accounts", exist_ok=True)

with open("web.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update /bots route to read bot_accounts and add UI
if "Добавить аккаунт бота" not in content:
    old_bots_html = """    <a href="/bots" class="active">🤖 Боты</a>
  </div>
</div>

<div class="card">"""
    new_bots_html = """    <a href="/bots" class="active">🤖 Боты</a>
  </div>
</div>

<div class="card">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <h3>Аккаунты ботов (для сообщений)</h3>
    <button onclick="addBotAccount()" style="background:var(--blue);color:#fff">+ Добавить аккаунт</button>
  </div>
  <div id="bot-accounts-list" style="margin-top:12px;font-size:13px;display:flex;gap:8px;">{accounts_html}</div>
</div>
<script>
async function addBotAccount() {
    const name = prompt("Введите название аккаунта (например, bot1):");
    if (!name) return;
    alert("Сейчас откроется браузер. Залогиньтесь в OLX, затем закройте окно, и аккаунт сохранится.");
    await fetch("/bots/add_account?name=" + encodeURIComponent(name));
    location.reload();
}
</script>

<div class="card">"""
    content = content.replace(old_bots_html, new_bots_html)

    old_tr = """                    <label><input type="checkbox" name="chat"> Открыть чат</label>
            </td>
            <td>
                    <button type="submit">▶ Запустить</button>"""
    new_tr = """                    <label><input type="checkbox" name="chat"> Открыть чат</label><br>
                    <input type="text" name="chat_message" placeholder="Текст сообщения" style="width:140px; margin-top:4px;"><br>
                    <select name="bot_account" style="width:140px; margin-top:4px;"><option value="none">Без аккаунта</option>{account_opts}</select>
            </td>
            <td>
                    <button type="submit">▶ Запустить</button>"""
    content = content.replace(old_tr, new_tr)

    old_bots_page = """@app.get("/bots")
def bots_page():
    allrows = storage.latest_rows()
    ads_html = ""
    for r in allrows:"""
    new_bots_page = """@app.get("/bots")
def bots_page():
    import os, glob
    acc_files = glob.glob("bot_accounts/*.json")
    acc_names = [os.path.basename(f).replace(".json", "") for f in acc_files]
    accounts_html = "".join([f"<span style='padding:4px 8px;background:var(--border);border-radius:4px;'>{n}</span>" for n in acc_names]) or "Нет аккаунтов"
    account_opts = "".join([f"<option value='{n}'>Аккаунт: {n}</option>" for n in acc_names])
    
    allrows = storage.latest_rows()
    ads_html = ""
    for r in allrows:"""
    content = content.replace(old_bots_page, new_bots_page)
    
    content = content.replace("return BOTS_HTML.format(ads_html=ads_html)", 'return BOTS_HTML.replace("{ads_html}", ads_html).replace("{accounts_html}", accounts_html).replace("{account_opts}", account_opts)')

    old_bots_start = """    actions = {
        "scroll": request.form.get("scroll") == "on",
        "click_phone": request.form.get("phone") == "on",
        "click_chat": request.form.get("chat") == "on",
    }
    task_ids = bot.start_bot(url, actions, amount)"""
    new_bots_start = """    actions = {
        "scroll": request.form.get("scroll") == "on",
        "click_phone": request.form.get("phone") == "on",
        "click_chat": request.form.get("chat") == "on",
        "chat_message": request.form.get("chat_message", "").strip(),
        "bot_account": request.form.get("bot_account", "none")
    }
    task_ids = bot.start_bot(url, actions, amount)"""
    content = content.replace(old_bots_start, new_bots_start)
    
add_acc_route = """
@app.get("/bots/add_account")
def bots_add_account():
    name = request.args.get("name", "bot")
    import threading
    def _run():
        import asyncio
        from playwright.async_api import async_playwright
        import os
        async def _login():
            try:
                from playwright_stealth import Stealth
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=False)
                    context = await browser.new_context(viewport={"width": 1280, "height": 720})
                    
                    async def handle_page(new_page):
                        if len(context.pages) <= 1:
                            return
                        try:
                            await asyncio.sleep(1)
                        except:
                            pass
                        url = new_page.url
                        allowed_domains = ["olx.kz", "olx.ua", "google.com", "facebook.com", "google.ru"]
                        if not any(domain in url for domain in allowed_domains):
                            try:
                                await new_page.close()
                            except:
                                pass
                    
                    context.on("page", handle_page)
                    page = await context.new_page()
                    await Stealth().apply_stealth_async(page)
                    
                    await page.goto("https://www.olx.kz/account/")
                    os.makedirs("bot_accounts", exist_ok=True)
                    state_path = f"bot_accounts/{name}.json"
                    
                    for _ in range(300):
                        if not browser.is_connected():
                            break
                        try:
                            await context.storage_state(path=state_path)
                            await asyncio.sleep(1)
                        except:
                            break
                    try:
                        await browser.close()
                    except:
                        pass
            except Exception as e:
                import traceback
                traceback.print_exc()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_login())
        loop.close()
        
    threading.Thread(target=_run, daemon=True).start()
    return "ok"
"""
if "@app.get(\"/bots/add_account\")" not in content:
    content = content.replace("@app.get(\"/bots/status\")", add_acc_route + "\n@app.get(\"/bots/status\")")

with open("web.py", "w", encoding="utf-8") as f:
    f.write(content)
print("web.py patched for bot accounts")
