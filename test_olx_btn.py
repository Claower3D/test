import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        print("Navigating...")
        await page.goto("https://www.olx.kz/d/obyavlenie/uborka-kvartir-ot-8-000-tg-opyt-9-let-okna-moem-besplatno-IDqTiG7.html", wait_until="domcontentloaded")
        print("Waiting for timeout...")
        await page.wait_for_timeout(5000)
        
        print("Taking screenshot...")
        await page.screenshot(path="artifacts/olx_test.png")
        
        print("Saving HTML...")
        html = await page.content()
        with open("artifacts/olx_test.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        print("Finding buttons...")
        btns = await page.locator("button, a").all()
        for b in btns:
            try:
                text = await b.inner_text()
                if "Позвонить" in text or "показать" in text.lower() or "Показать" in text or "SMS" in text:
                    print(f"FOUND BUTTON TEXT: {text}")
                    html_snippet = await b.evaluate("el => el.outerHTML")
                    print(f"HTML: {html_snippet}")
            except:
                pass
                
        await browser.close()

asyncio.run(main())
