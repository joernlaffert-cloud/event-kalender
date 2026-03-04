import json
from .base_scraper import EventScraper
from bs4 import BeautifulSoup

class StereowerkScraper(EventScraper):
    def __init__(self):
        super().__init__("Stereowerk", "https://www.stereowerk.de/events")
        
    def scrape_events_text(self) -> str:
        print(f"[{self.name}] Fetching special HTML...")
        html = self.fetch_html(self.base_url)
        if not html:
            return ""
            
        soup = BeautifulSoup(html, "html.parser")
        
        # Wix sites often put widgets in iframes. Let's try to extract iframes
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src')
            if src and 'events' in src.lower():
                print(f"[{self.name}] Found inner events iframe, fetching it...")
                html = self.fetch_html(src)
                soup = BeautifulSoup(html, "html.parser")
                break
        
        # Now clean normally
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.extract()
            
        text = soup.get_text(separator=' ')
        
        # Collapse whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        combined_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        with open(f"/tmp/debug_{self.name.replace(' ', '_')}.txt", "w", encoding="utf-8") as f:
             f.write(combined_text)
             
        return combined_text
