import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        await page.goto("https://www.olx.kz/account/")
        print("Page loaded")
        
        # Look for Google login button and click it
        google_btn = await page.wait_for_selector("text=Продолжить через Google", timeout=5000)
        if google_btn:
            print("Found Google button, clicking...")
            async with context.expect_page() as new_page_info:
                await google_btn.click()
            new_page = await new_page_info.value
            print(f"New page opened: {new_page.url}")
            await new_page.wait_for_load_state()
            print(f"New page title: {await new_page.title()}")
        await browser.close()

asyncio.run(test())
