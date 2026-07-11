from playwright.sync_api import sync_playwright
import time

def test_search_id(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            viewport={"width": 390, "height": 844}
        )
        page = context.new_page()
        
        # Extract ID from URL
        # e.g., https://www.olx.kz/d/obyavlenie/moskitnye-setki-astana-besplatnyy-vyezd-mastera-IDqXF2L.html
        ad_id = url.split("-ID")[-1].replace(".html", "")
        print(f"Extracted ID: {ad_id}")
        
        page.goto("https://www.olx.kz/")
        print("Went to homepage.")
        time.sleep(2)
        
        # Find search input
        page.fill('input[data-testid="search-input"]', ad_id)
        print("Filled search.")
        time.sleep(1)
        
        page.keyboard.press("Enter")
        print("Pressed Enter.")
        time.sleep(4)
        
        print("Current URL:", page.url)
        browser.close()

test_search_id("https://www.olx.kz/d/obyavlenie/moskitnye-setki-astana-besplatnyy-vyezd-mastera-IDqXF2L.html")
