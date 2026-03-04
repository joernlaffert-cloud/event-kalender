import os
import json
from scrapers.base_scraper import EventScraper
from llm_parser import LLMEventParser
from ics_builder import ICSBuilder

class GenericWebScraper(EventScraper):
    def scrape_events_text(self) -> str:
        print(f"Fetching from {self.base_url}...")
        html = self.fetch_html(self.base_url)
        if not html:
            return ""
        text = self.clean_html_to_text(html)
        return text

def load_sources_from_config(config_file="config.json"):
    from scrapers.stereowerk_scraper import StereowerkScraper
    
    sources = []
    if not os.path.exists(config_file):
        print(f"Warning: {config_file} not found. Creating default empty config.")
        return sources
        
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        for s in data.get("sources", []):
            if s.get("enabled", False):
                name = s.get("name")
                # Route to specialized scrapers if they exist
                if s.get("name") == "Stereowerk":
                    sources.append(StereowerkScraper())
                elif s.get("name") == "Brain Klub":
                    from scrapers.brainklub_scraper import BrainKlubScraper
                    sources.append(BrainKlubScraper())
                elif s.get("name") == "Konzertkasse":
                    from scrapers.konzertkasse_scraper import KonzertkasseScraper
                    sources.append(KonzertkasseScraper())
                else:
                    sources.append(GenericWebScraper(name, s.get("url")))
    except Exception as e:
        print(f"Error loading configuration: {e}")
        
    return sources

def main():
    print("=== Braunschweig Event Calendar Automation ===")
    
    sources = load_sources_from_config()
    if not sources:
        print("No active sources found in config.json. Please enable some and try again.")
        return
    
    print(f"Loaded {len(sources)} active sources to scrape.")
    
    # 1. Scrape all raw text
    all_raw_text = []
    for source in sources:
        try:
            text = source.scrape_events_text()
            if text:
                all_raw_text.append(f"--- START SITE: {source.name} ---\n{text}\n--- END SITE: {source.name} ---")
        except Exception as e:
            print(f"Error gathering text from {source.name}: {e}")
            
    combined_text = "\n\n".join(all_raw_text)
    
    if not combined_text.strip():
        print("No text fetched from any source. Using a fallback dummy string to test the LLM and ICS pipeline.")
        combined_text = """
        Hier sind einige kommende Events im Dummy Club:
        - 15. August 2026: Große 80er Party, Start 22:00 Uhr, Dummy Club, Party
        - 20. August 2026: Theateraufführung "Hamlet", Start 19:30 Uhr, Staatstheater Dummy, Theater
        - 01. September 2026: Rock Konzert mit Band X, 20:00 Uhr, Dummy Halle, Musik
        """
        
    # 2. Extract Event JSON via Local LLM
    print("\nStarting LLM Extraction...")
    parser = LLMEventParser(model_name="hf.co/chatpdflocal/Qwen2.5.1-Coder-14B-Instruct-GGUF:Q4_K_M")
    parsed_events = parser.parse_events(combined_text)
    
    print(f"LLM successfully extracted {len(parsed_events)} events.")
    
    # 3. Build ICS Calendars
    if parsed_events:
        print("\nBuilding ICS Calendars...")
        builder = ICSBuilder()
        builder.build_calendars(parsed_events)
        print("\nDone! Check the '/output' folder.")
    else:
        print("\nNo events extracted to build calendars.")

if __name__ == "__main__":
    main()
