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
        
        # We can use msedge if needed, but chromium is default
        context = await p.chromium.launch_persistent_context(temp_dir, **browser_args)
        page = context.pages[0] if context.pages else await context.new_page()
        
        print("Opening WhatsApp Web...")
        await page.goto("https://web.whatsapp.com/")
        
        print("Waiting for you to click on any chat. You have 30 seconds...")
        await asyncio.sleep(15)
        
        try:
            footer = await page.wait_for_selector("footer", timeout=15000)
            html = await footer.inner_html()
            with open("footer_debug.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("Footer HTML dumped to footer_debug.html!")
        except Exception as e:
            print("Failed to find footer:", e)
            
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
