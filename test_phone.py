from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page()
    # Using the ID from the screenshot: 398356944
    page.goto("https://www.olx.kz/d/obyavlenie/remont-stiralnyh-mashin-almaty-nedorogo-i-kachestvenno-IDqYfP6.html")
    page.wait_for_timeout(3000)
    
    # Click show phone
    btn = page.locator('button[data-testid="contact-phone"]')
    if btn.count() == 0:
        btn = page.locator('button:has-text("Показать")')
        
    if btn.count() > 0:
        print("Clicking show phone...")
        btn.first.click()
        page.wait_for_timeout(3000)
        
        # Now print the HTML of the revealed phone number
        html = page.locator('button[data-testid="contact-phone"]').inner_html() if page.locator('button[data-testid="contact-phone"]').count() > 0 else page.content()
        print("Revealed HTML:")
        print(html)
        
        # Test clicking it
        number = page.locator('a[href^="tel:"]')
        if number.count() > 0:
            print("Found tel link!")
            # don't click it physically because it'll crash headless if no handler, or maybe it won't.
        else:
            print("No tel link found!")
            
    b.close()
