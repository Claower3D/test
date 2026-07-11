from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        viewport={"width": 390, "height": 844}
    )
    page.goto("https://www.olx.kz/")
    page.wait_for_timeout(3000)
    page.fill('input[data-testid="search-input"]', "355018285")
    page.keyboard.press("Enter")
    page.wait_for_timeout(5000)
    print("URL after enter:", page.url)
    browser.close()
