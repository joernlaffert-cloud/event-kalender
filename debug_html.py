from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://staatstheater-braunschweig.de/spielplan/kalender/", wait_until="networkidle")
    
    html = page.content()
    
    with open("/tmp/raw_stereowerk.html", "w", encoding="utf-8") as f:
        f.write(html)
        
    print("Done writing HTML.")
    browser.close()
