import asyncio
from playwright.sync_api import sync_playwright

def test_type():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://www.olx.kz/")
        page.wait_for_timeout(3000)
        
        # Type in search box
        page.fill('input[data-testid="search-input"]', "398356944")
        page.wait_for_timeout(1000)
        
        # Press enter
        page.keyboard.press("Enter")
        page.wait_for_timeout(3000)
        
        html = page.content()
        if "398356944" in html:
            print("Successfully typed and searched!")
        else:
            print("Failed to search!")
            
        browser.close()

test_type()
