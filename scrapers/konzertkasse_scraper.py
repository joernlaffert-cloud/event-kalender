from bs4 import BeautifulSoup
from scrapers.base_scraper import EventScraper
import re

class KonzertkasseScraper(EventScraper):
    def __init__(self):
        super().__init__("Konzertkasse", "")
        self.categories = [
            "https://www.konzertkasse.de/event-category/konzerte/",
            "https://www.konzertkasse.de/event-category/kultur/",
            "https://www.konzertkasse.de/event-category/humor/",
            "https://www.konzertkasse.de/event-category/sport/",
            "https://www.konzertkasse.de/event-category/freizeit/"
        ]

    def scrape_events_text(self) -> str:
        all_events_text = []
        
        for url in self.categories:
            print(f"[{self.name}] Fetching {url}...")
            html = self.fetch_html_fast(url)
            if not html:
                continue
                
            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select("div.event-card")
            
            for card in cards:
                title_elem = card.select_one("h3.event-card-title")
                date_elem = card.select_one("span.event-card-date")
                venue_elem = card.select_one("span.event-card-venue")
                
                title = title_elem.get_text(strip=True) if title_elem else "Unbekannter Titel"
                date = date_elem.get_text(strip=True) if date_elem else "Unbekanntes Datum"
                venue = venue_elem.get_text(strip=True) if venue_elem else "Unbekannter Ort"
                
                # Filter for Braunschweig events only to save LLM tokens
                if "braunschweig" in venue.lower():
                    # Clean up texts
                    date = re.sub(r'^\d{2}\.\d{2}\.\d{4}', lambda m: m.group(), date) # Basic cleanup
                    event_str = f"Event: {title} | Datum: {date} | Ort: {venue}"
                    all_events_text.append(event_str)
                    
        if not all_events_text:
            return ""
            
        return "\n".join(set(all_events_text)) # Use set to easily remove duplicates
