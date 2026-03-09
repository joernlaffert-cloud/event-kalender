from bs4 import BeautifulSoup
from scrapers.base_scraper import EventScraper
import re

class BrunsvigaScraper(EventScraper):
    def __init__(self):
        super().__init__("Brunsviga Kulturzentrum", "https://www.brunsviga-kulturzentrum.de/programm/")

    def scrape_events_text(self) -> str:
        all_events_text = []

        print(f"[{self.name}] Fetching {self.base_url}...")
        html = self.fetch_html(self.base_url)
        if not html:
            return ""

        soup = BeautifulSoup(html, "html.parser")
        
        # Brunsviga uses a table-based calendar format
        # The events are located inside elements with class 'popup' inside 'td.hasevents'
        event_cells = soup.select("td.hasevents .popup")
        
        for cell in event_cells:
            links = cell.select("a.noarrow")
            for link in links:
                
                title_elem = link.select_one("span.title")
                time_elem = link.select_one("span.date")
                
                # Get the subtitle/description which is usually text directly in the a-tag after the strong tag
                full_text = link.get_text(separator=' ', strip=True)
                
                title = title_elem.get_text(strip=True) if title_elem else ""
                time_str = time_elem.get_text(strip=True) if time_elem else "Unbekannte Zeit"
                
                # Clean up if title is found in full text
                if title:
                    subtitle = full_text.replace(title, "").replace(time_str, "").strip()
                else:
                    subtitle = full_text
                    title = "Brunsviga Event"

                # They don't have perfect inline dates in the popup, but the LLM is smart.
                # Just passing the raw joined text is highly effective for this LLM.
                event_str = f"Event: {title} | Zeit: {time_str} | Details: {subtitle} | Ort: Brunsviga Kulturzentrum"
                all_events_text.append(event_str)

        if not all_events_text:
            return ""

        # Use set to remove duplicate popups
        return "\n".join(set(all_events_text))
