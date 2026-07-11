from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page()
    page.goto('https://www.olx.kz/list/q-355018285/')
    page.wait_for_timeout(3000)
    html = page.content()
    import re
    links = set(re.findall(r'href="([^"]*)"', html))
    for link in links:
        if '/d/obyavlenie/' in link:
            print(link)
    b.close()
