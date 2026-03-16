from bs4 import BeautifulSoup
from scrapers.base_scraper import EventScraper
import re

class BrunsvigaScraper(EventScraper):
    def __init__(self):
        super().__init__("Brunsviga Kulturzentrum", "https://www.brunsviga-kulturzentrum.de/programm/")

    def scrape_events_text(self) -> str:
        print(f"[{self.name}] Fetching {self.base_url}...")
        html = self.fetch_html_fast(self.base_url)
        if not html:
            return ""

        soup = BeautifulSoup(html, "html.parser")
        
        # Target the main content container if possible
        # Based on typical structures, look for 'programm' or generic 'content'
        content = soup.find('div', id='content') or soup.find('main') or soup
        
        # Remove noise
        for tag in content(["script", "style", "nav", "footer", "header", "meta", "link", "aside"]):
            tag.extract()

        text = content.get_text(separator='\n')
        
        # Collapse multiple newlines/spaces
        lines = (line.strip() for line in text.splitlines())
        text = '\n'.join(line for line in lines if line)
        
        # Deduplicate consecutive identical lines to reduce noise for the LLM
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if not cleaned_lines or line != cleaned_lines[-1]:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
