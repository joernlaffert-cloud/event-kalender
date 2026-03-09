from scrapers.base_scraper import EventScraper
from bs4 import BeautifulSoup

class BrainKlubScraper(EventScraper):
    def __init__(self):
        super().__init__("Brain Klub", "https://www.brainklub.de/")
        
    def scrape_events_text(self) -> str:
        print(f"[{self.name}] Fetching special HTML...")
        html = self.fetch_html(self.base_url)
        if not html:
            return ""
            
        soup = BeautifulSoup(html, "html.parser")
        
        # Brain Klub uses an iframe for their content
        iframe = soup.find('iframe')
        if iframe and iframe.get('src'):
            iframe_url = iframe['src']
            if not iframe_url.startswith('http'):
                iframe_url = "https://www.brainklub.de" + iframe_url if iframe_url.startswith('/') else "https://www.brainklub.de/" + iframe_url
            
            print(f"[{self.name}] Found iframe, fetching {iframe_url}...")
            html = self.fetch_html(iframe_url)
            
        return self.clean_html_to_text(html)
