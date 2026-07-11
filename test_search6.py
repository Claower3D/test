from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page()
    page.goto('https://www.olx.kz/list/q-398301615/')
    page.wait_for_timeout(3000)
    html = page.content()
    import re
    links = set(re.findall(r'href="([^"]*)"', html))
    found = False
    for link in links:
        if '/d/obyavlenie/' in link and 'reason=extended_search_no_results_last_resort' not in link:
            print("Found ad link:", link)
            found = True
    if not found:
        print("No exact ad found.")
    b.close()
