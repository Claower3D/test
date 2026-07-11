import asyncio
from playwright.async_api import async_playwright
import sys

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--block-new-web-contents"]
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        # We will try to open a new tab using JS and see if it is blocked
        await page.goto("about:blank")
        await page.evaluate("window.open('https://google.com')")
        
        # Check if a second page was opened
        print(f"Number of pages in context: {len(context.pages)}")
        await asyncio.sleep(5)
        await browser.close()

asyncio.run(test())
