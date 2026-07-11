import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import os

name = "testlogin"

async def _login():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        await context.add_init_script("window.open = () => null;")
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
            except Exception as e:
                print(f"Save state error: {e}")
                break
        
        try:
            await browser.close()
        except:
            pass

asyncio.run(_login())
