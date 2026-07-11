import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        await page.goto("https://www.olx.kz/account/")
        print("Page title:", await page.title())
        await asyncio.sleep(5)
        print("Done")
        await browser.close()

asyncio.run(test())
