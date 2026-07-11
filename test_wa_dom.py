import asyncio
import os
from playwright.async_api import async_playwright

async def main():
    temp_dir = os.path.abspath("whatsapp_profile")
    async with async_playwright() as p:
        browser_args = {
            "headless": False,
            "viewport": {"width": 1280, "height": 720},
            "args": ["--disable-blink-features=AutomationControlled"]
        }
        context = await p.chromium.launch_persistent_context(temp_dir, **browser_args)
        page = context.pages[0] if context.pages else await context.new_page()
        
        await page.goto("https://web.whatsapp.com/")
        print("Waiting for page to load...")
        await asyncio.sleep(10)
        
        html = await page.content()
        with open("wa_dom.txt", "w", encoding="utf-8") as f:
            f.write(html)
        print("DOM dumped to wa_dom.txt")
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
