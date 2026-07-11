import asyncio
import os
from playwright.async_api import async_playwright
import winreg
import shlex

async def main():
    exe_path = None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice") as key:
            prog_id = winreg.QueryValueEx(key, "ProgId")[0]
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, rf"{prog_id}\shell\open\command") as key:
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
            await page.wait_for_selector('#pane-side', timeout=300000) # 5 минут на скан
            print("✅ Авторизация успешна! Сессия сохранена.")
            await asyncio.sleep(3) # даем кукам записаться
        except:
            print("⏳ Время ожидания истекло или окно было закрыто.")
            
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
