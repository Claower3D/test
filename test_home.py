from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        viewport={"width": 390, "height": 844}
    )
    page = context.new_page()
    page.goto("https://www.olx.kz/")
    page.wait_for_timeout(3000)
    page.screenshot(path="olx_home.png")
    
    # Dump HTML to find the search input
    with open("olx_home.html", "w", encoding="utf-8") as f:
        f.write(page.content())
        
    browser.close()
