from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page()
    page.goto("https://www.olx.kz/d/obyavlenie/remont-stiralnyh-mashin-almaty-nedorogo-i-kachestvenno-IDqYfP6.html")
    page.wait_for_timeout(3000)
    page.screenshot(path="olx_ad.png")
    with open("olx_ad.html", "w", encoding="utf-8") as f:
        f.write(page.content())
    b.close()
