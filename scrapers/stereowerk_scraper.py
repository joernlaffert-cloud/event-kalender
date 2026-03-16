from scrapers.base_scraper import EventScraper
from playwright.sync_api import sync_playwright
import time
from bs4 import BeautifulSoup

class StereowerkScraper(EventScraper):
    def __init__(self):
        super().__init__("Stereowerk", "https://www.stereowerk.de/events")

    def scrape_events_text(self) -> str:
        print(f"[{self.name}] Booting Playwright browser for {self.base_url}...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(self.base_url, wait_until="load", timeout=20000)
                
                # Try to dismiss Wix popup
                try:
                    page.keyboard.press("Escape")
                    time.sleep(1)
                except:
                    pass
                    
                try:
                    page.click('[aria-label="Close dialog"]', timeout=2000)
                    time.sleep(1)
                except:
                    pass
                    
                try:
                    page.click('path[d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"]', timeout=2000)
                    time.sleep(1)
                except:
                    pass

                time.sleep(5)  # Wait longer for events to be fully visible (Wix is slow)
                html = page.content()
                browser.close()
                
                if not html:
                    return ""
                
                return self.clean_html_to_text(html)
        except Exception as e:
            print(f"[{self.name}] Error rendering {self.base_url} with Playwright: {e}")
            return ""
