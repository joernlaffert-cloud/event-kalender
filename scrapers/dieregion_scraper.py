from bs4 import BeautifulSoup
import requests
import datetime
from scrapers.base_scraper import EventScraper

class DieRegionScraper(EventScraper):
    def __init__(self):
        super().__init__("Stadt Braunschweig (die-region.de)", "https://braunschweig.die-region.de/")
        # We need to hit the form list action URL directly to get the HTML, since the main page loads it dynamically
        self.api_url = "https://braunschweig.die-region.de/?tx_gcevents_eventlisting%5Baction%5D=list&tx_gcevents_eventlisting%5Bcontroller%5D=Event&cHash=22a28396330d397ce8b437bf068a04e6#collapsible"

    def fetch_html(self, url: str) -> str:
        # We override fetch_html because we need to query the custom endpoint with specific params
        params = {
            "tx_gcevents_eventlisting[keyWord]": "",
            "tx_gcevents_eventlisting[eventtype]": "0",  # Alle Veranstaltungsarten
            "tx_gcevents_eventlisting[city]": "0",       # Alle Orte
        }
        
        # We can also dynamically pass the current date to only fetch upcoming events
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        params["tx_gcevents_eventlisting[startdate]"] = today
        
        print(f"[{self.name}] Fetching active events list from die-region.de...")
        try:
            response = requests.get(self.api_url, params=params, timeout=15)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"[{self.name}] Error fetching data: {e}")
            return ""

    def extract_text(self, html: str) -> str:
        if not html:
            return ""
        
        soup = BeautifulSoup(html, "html.parser")
        events = soup.find_all("div", class_="event-list__item")
        
        if not events:
            return "No events found on die-region.de."

        extracted_texts = []
        extracted_texts.append(f"Source: {self.name}")
        
        for event in events:
            # 1. Headline
            headline_tag = event.find("h2", class_="event-list__headline")
            title = headline_tag.get_text(strip=True) if headline_tag else "Unknown Title"
            
            # 2. Date
            date_tag = event.find("p", class_="event-list__date")
            date_text = date_tag.get_text(separator=" ", strip=True) if date_tag else "Unknown Date"
            
            # 3. Info Items (Location & Time)
            info_items = event.find_all("span", class_="event-list__info-item")
            location_text = "Unknown Location"
            time_text = "Unknown Time"
            
            for index, item in enumerate(info_items):
                # The first item is usually the location, the second is the time
                # We can also look at the SVG icon if needed, but index is usually sufficient
                text = item.get_text(separator=" ", strip=True)
                if index == 0:
                    location_text = text
                elif index == 1:
                    time_text = text

            event_str = f"Event: {title}\nDate: {date_text}\nTime: {time_text}\nLocation: {location_text}"
            extracted_texts.append(event_str)
        
        return "\n\n".join(extracted_texts)

    def scrape_events_text(self) -> str:
        html = self.fetch_html(self.api_url)
        if not html:
            return ""
        return self.extract_text(html)
