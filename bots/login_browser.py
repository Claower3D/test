"""
Отдельный скрипт для входа в аккаунт OLX.
"""
import asyncio
import sys
import os

name = sys.argv[1] if len(sys.argv) > 1 else "bot"

async def _login():
    from playwright.async_api import async_playwright
    
    # Ищем путь к Brave (дефолтному браузеру) для 100% обхода защиты OLX
    import winreg
    import shlex
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
        
    async with async_playwright() as p:
        browser_args = {
            "headless": False,
            "viewport": {"width": 1280, "height": 720},
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-infobars",
                "--disable-extensions"
            ]
        }
        if exe_path:
            browser_args["executable_path"] = exe_path
        
        import tempfile
        temp_dir = tempfile.mkdtemp()
        
        try:
            context = await p.chromium.launch_persistent_context(temp_dir, **browser_args)
        except Exception:
            # Фолбек на Edge/Chrome
            try:
                browser_args["channel"] = "msedge"
                browser_args.pop("executable_path", None)
                context = await p.chromium.launch_persistent_context(temp_dir, **browser_args)
            except Exception:
                browser_args.pop("channel", None)
                context = await p.chromium.launch_persistent_context(temp_dir, **browser_args)
                
        browser = context.browser if context.browser else context
        
        if context.pages:
            target_page = context.pages[0]
        else:
            target_page = await context.new_page()
            
        # Умный способ: закрываем только левые вкладки (adware/рекламу), но разрешаем OAuth (Google, Facebook, Apple)
        async def on_page_created(new_page):
            if new_page != target_page:
                await asyncio.sleep(1.0) # даем вкладке секунду определиться с URL
                try:
                    url = new_page.url.lower()
                    allowed = ["google", "apple", "facebook", "olx.kz", "live.com", "microsoft", "about:blank"]
                    if any(domain in url for domain in allowed):
                        return # разрешаем вход через сторонние сервисы
                    await new_page.close()
                except:
                    pass
        
        context.on("page", on_page_created)
        
        from playwright_stealth import Stealth
        await Stealth().apply_stealth_async(target_page)
        
        url = "https://www.olx.kz/account/"
        await target_page.goto(url)
        
        import os
        os.makedirs("bot_accounts", exist_ok=True)
        state_path = f"bot_accounts/{name}.json"
        
        print(f"Browser open. Login to OLX. Saving to: {state_path}")
        
        for _ in range(300):
            try:
                if len(context.pages) == 0:
                    break
            except:
                break
                
            # Перехват успешного входа
            try:
                current_url = target_page.url
                # Если перенаправило в личный кабинет, значит вход успешен
                if "myaccount" in current_url:
                    # Даем кукам немного времени обновиться, сохраняем и закрываем
                    await asyncio.sleep(1.5)
                    await context.storage_state(path=state_path)
                    print("Вход успешно перехвачен! Сохраняем аккаунт.")
                    break
            except:
                pass
                
            try:
                await context.storage_state(path=state_path)
            except:
                break
            await asyncio.sleep(1)
        
        try:
            await context.close()
            await browser.close()
        except:
            pass

asyncio.run(_login())
