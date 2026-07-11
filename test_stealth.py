import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def _login():
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(viewport={"width": 1280, "height": 720})
            
            # Automatically close any popups that are not OLX or Auth providers
            async def handle_page(new_page):
                # If this is the main page, don't touch it
                if len(context.pages) <= 1:
                    return
                try:
                    await asyncio.sleep(1)
                except:
                    pass
                url = new_page.url
                print(f"Detected new popup/tab: {url}")
                allowed_domains = ["olx.kz", "olx.ua", "google.com", "facebook.com", "google.ru"]
                if not any(domain in url for domain in allowed_domains):
                    print(f"Closing unauthorized tab: {url}")
                    try:
                        await new_page.close()
                    except Exception as e:
                        print(f"Failed to close tab: {e}")

            context.on("page", handle_page)
            
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)
            await page.goto("https://www.olx.kz/account/")
            
            # Keep browser alive for testing
            await asyncio.sleep(20)
            await browser.close()
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(_login())
