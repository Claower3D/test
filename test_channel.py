import asyncio
from playwright.async_api import async_playwright
import playwright_stealth

async def _login():
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                channel="chrome",
                headless=False,
                args=["--disable-blink-features=AutomationControlled"]
            )
            print("Chrome channel launch OK")
            await browser.close()
    except Exception as e:
        print("Error launching chrome channel:", e)
        
        print("Trying msedge...")
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    channel="msedge",
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"]
                )
                print("msedge channel launch OK")
                await browser.close()
        except Exception as e2:
            print("Error launching msedge channel:", e2)

asyncio.run(_login())
