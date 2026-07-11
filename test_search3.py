from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://www.olx.kz/list/q-IDqXF2L/")
    page.wait_for_timeout(3000)
    html = page.content()
    import re
    links = set(re.findall(r'href="([^"]*)"', html))
    for link in links:
        if '/d/obyavlenie/' in link:
            print(link)
    browser.close()
