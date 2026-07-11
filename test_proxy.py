import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        proxy = {
            "server": "http://176.9.154.69:9253",
            "username": "imr3KB3tsCW6",
            "password": "D6RiYk66Uz"
        }
        print("Creating context with proxy...")
        try:
            context = await browser.new_context(proxy=proxy)
            page = await context.new_page()
            print("Navigating...")
            await page.goto("https://bot.sannysoft.com", timeout=15000)
            print("Title:", await page.title())
        except Exception as e:
            print("Error:", e)
        finally:
            await browser.close()

asyncio.run(run())
