import codecs
import os

# 1. Сначала исправим whatsapp_sender.py чтобы он сохранял сессию локально
sender_code = ""
with open("whatsapp_sender.py", "r", encoding="utf-8") as f:
    sender_code = f.read()
    
# Заменяем использование tempfile на локальную папку
if "import tempfile" in sender_code:
    sender_code = sender_code.replace("import tempfile\n    temp_dir = tempfile.mkdtemp()", 'temp_dir = os.path.abspath("whatsapp_profile")\n    os.makedirs(temp_dir, exist_ok=True)')
    with open("whatsapp_sender.py", "w", encoding="utf-8") as f:
        f.write(sender_code)

# 2. Создаем скрипт для авторизации whatsapp_login.py
login_script = """import asyncio
import os
from playwright.async_api import async_playwright
import winreg
import shlex

async def main():
    exe_path = None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\Shell\\Associations\\UrlAssociations\\http\\UserChoice") as key:
            prog_id = winreg.QueryValueEx(key, "ProgId")[0]
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, rf"{prog_id}\\shell\\open\\command") as key:
            command = winreg.QueryValueEx(key, "")[0]
        parts = shlex.split(command)
        if parts and os.path.exists(parts[0]):
            exe_path = parts[0]
    except:
        pass

    temp_dir = os.path.abspath("whatsapp_profile")
    os.makedirs(temp_dir, exist_ok=True)
    
    async with async_playwright() as p:
        browser_args = {
            "headless": False,
            "viewport": {"width": 1280, "height": 720},
            "args": ["--disable-blink-features=AutomationControlled"]
        }
        if exe_path:
            browser_args["executable_path"] = exe_path

        try:
            context = await p.chromium.launch_persistent_context(temp_dir, **browser_args)
        except Exception:
            try:
                browser_args["channel"] = "msedge"
                browser_args.pop("executable_path", None)
                context = await p.chromium.launch_persistent_context(temp_dir, **browser_args)
            except Exception:
                browser_args.pop("channel", None)
                context = await p.chromium.launch_persistent_context(temp_dir, **browser_args)

        page = context.pages[0] if context.pages else await context.new_page()

        print("Открываю WhatsApp Web для авторизации...")
        await page.goto("https://web.whatsapp.com/")
        
        print("Пожалуйста, отсканируйте QR-код. Окно закроется автоматически после успешного входа.")
        
        try:
            # Ждем появления списка чатов, что означает успешный вход
            await page.wait_for_selector('div[title="Чаты"], div[title="Chats"]', timeout=300000) # 5 минут на скан
            print("✅ Авторизация успешна! Сессия сохранена.")
            await asyncio.sleep(3) # даем кукам записаться
        except:
            print("⏳ Время ожидания истекло или окно было закрыто.")
            
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
"""
with open("whatsapp_login.py", "w", encoding="utf-8") as f:
    f.write(login_script)


# 3. Добавляем эндпоинт и кнопку в web.py
content = codecs.open('web.py', 'r', 'utf-8', errors='replace').read()

endpoint_code = """
@app.post("/whatsapp_login")
def whatsapp_login_endpoint():
    import subprocess
    try:
        subprocess.Popen(["python", "whatsapp_login.py"], shell=False)
        return jsonify({"status": "запущено"})
    except Exception as e:
        return jsonify({"status": "ошибка", "error": str(e)})

@app.post("/whatsapp_send")"""

if "/whatsapp_login" not in content:
    content = content.replace('@app.post("/whatsapp_send")', endpoint_code)

button_html = """<div style="display: flex; gap: 12px; flex-wrap: wrap;">
                    <button onclick="runLogin()" style="flex: 1; min-width: 150px; padding: 14px; font-size: 14px; border-radius: 6px; background: var(--blue); color: #fff; font-weight: bold; border: none; cursor: pointer; transition: 0.2s; margin-bottom: 8px;">🔑 Подключить WhatsApp</button>
                    <button onclick="runSender()" style="flex: 1; min-width: 150px; padding: 14px; font-size: 14px; border-radius: 6px; background: var(--danger); color: #fff; font-weight: bold; border: none; cursor: pointer; transition: 0.2s; margin-bottom: 8px;">🚀 Запустить рассылку</button>
                </div>"""

# Replace the old buttons div
old_buttons = """<div style="display: flex; gap: 12px; flex-wrap: wrap;">
                    <button onclick="runSender()" style="flex: 1; min-width: 150px; padding: 14px; font-size: 14px; border-radius: 6px; background: var(--danger); color: #fff; font-weight: bold; border: none; cursor: pointer; transition: 0.2s;">🚀 Запустить рассылку</button>
                </div>"""

if old_buttons in content:
    content = content.replace(old_buttons, button_html)

# Add js for runLogin
js_code = """function runLogin() {
            const statusDiv = document.getElementById("run-status");
            statusDiv.style.display = "block";
            statusDiv.style.borderColor = "var(--blue)";
            statusDiv.style.color = "var(--blue)";
            statusDiv.innerText = "Открываем браузер для привязки WhatsApp...";
            
            fetch("/whatsapp_login", { method: "POST" })
                .then(res => res.json())
                .then(data => {
                    if(data.status === "запущено") {
                        statusDiv.innerText = "Браузер открыт! Отсканируйте QR-код. Окно само закроется после входа.";
                        statusDiv.style.color = "var(--accent)";
                        statusDiv.style.borderColor = "var(--accent)";
                    } else {
                        statusDiv.innerText = "Ошибка: " + data.error;
                    }
                });
        }
        function runSender()"""

if "function runLogin()" not in content:
    content = content.replace("function runSender()", js_code)

with codecs.open('web.py', 'w', 'utf-8') as f:
    f.write(content)
