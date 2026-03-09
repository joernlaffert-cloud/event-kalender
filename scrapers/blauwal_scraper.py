from scrapers.base_scraper import EventScraper

class BlauWalScraper(EventScraper):
    def __init__(self):
        super().__init__("Blau Wal", "https://blau-wal.de/#veranstaltungskalender")

    def scrape_events_text(self) -> str:
        html = self.fetch_html(self.base_url)
        if not html:
            return ""
        return self.clean_html_to_text(html)
