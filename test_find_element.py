import asyncio
import os
import winreg
import shlex
from playwright.async_api import async_playwright

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
    
    async with async_playwright() as p:
        browser_args = {
            "headless": False,
            "viewport": {"width": 1280, "height": 720},
            "args": ["--disable-blink-features=AutomationControlled"]
        }
        if exe_path:
            browser_args["executable_path"] = exe_path

        context = await p.chromium.launch_persistent_context(temp_dir, **browser_args)
        page = context.pages[0] if context.pages else await context.new_page()
        
        await page.goto("https://web.whatsapp.com/")
        print("Waiting 15 seconds for WhatsApp to load...")
        await asyncio.sleep(15)
        
        # Check various selectors
        selectors = [
            '#pane-side', 
            'div[title="Чаты"]', 
            'div[title="Chats"]', 
            'span[data-icon="chat"]',
            'div[aria-label="Список чатов"]',
            'button[aria-label="Новый чат"]',
            'div[data-testid="chat-list"]',
            'div[id="side"]'
        ]
        
        for sel in selectors:
            try:
                elem = await page.query_selector(sel)
                if elem:
                    print(f"FOUND: {sel}")
                else:
                    print(f"NOT FOUND: {sel}")
            except Exception as e:
                print(f"Error checking {sel}: {e}")
                
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
