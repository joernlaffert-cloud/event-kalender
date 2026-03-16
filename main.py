import os
import json
from scrapers.base_scraper import EventScraper
from llm_parser import LLMEventParser
from ics_builder import ICSBuilder

class GenericWebScraper(EventScraper):
    def scrape_events_text(self) -> str:
        # Note: We rely on the caller to handle print/logging
        html = self.fetch_html(self.base_url)
        if not html:
            return ""
        text = self.clean_html_to_text(html)
        return text

from scrapers.stereowerk_scraper import StereowerkScraper
from scrapers.rausgegangen_scraper import RausgegangenScraper
from scrapers.brainklub_scraper import BrainKlubScraper
from scrapers.konzertkasse_scraper import KonzertkasseScraper
from scrapers.brunsviga_scraper import BrunsvigaScraper
from scrapers.dieregion_scraper import DieRegionScraper
from scrapers.blauwal_scraper import BlauWalScraper
from scrapers.barnabys_scraper import BarnabysScraper
from scrapers.komoedie_scraper import KomoedieScraper
from scrapers.staatstheater_scraper import StaatstheaterScraper
from scrapers.lions_scraper import LionsScraper
from scrapers.kufa_scraper import KufaScraper
from scrapers.westand_scraper import WestandScraper
from scrapers.landesmuseen_scraper import LandesmuseenScraper
from scrapers.eventbrite_scraper import EventbriteScraper
from scrapers.loewen_scraper import LoewenScraper
from scrapers.vhs_scraper import VHSScraper

def load_sources_from_config(config_file="config.json", log_callback=print, enabled_scrapers=None):
    print(f"DEBUG: Inside load_sources_from_config (manual override: {enabled_scrapers is not None})...")
    sources = []
    if not os.path.exists(config_file):
        print("DEBUG: config_file not found")
        return sources
        
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        for s in data.get("sources", []):
            name = s.get("name")
            # Logic: If manual list provided, use it. Otherwise use 'enabled' flag from config.
            is_enabled = False
            if enabled_scrapers is not None:
                is_enabled = name in enabled_scrapers
            else:
                is_enabled = s.get("enabled", False)

            if is_enabled:
                print(f"DEBUG: Initializing {name}...")
                if name == "Stereowerk":
                    sources.append(StereowerkScraper())
                elif name == "Rausgegangen":
                    sources.append(RausgegangenScraper())
                elif name == "Brain Klub":
                    sources.append(BrainKlubScraper())
                elif name == "Konzertkasse":
                    sources.append(KonzertkasseScraper())
                elif name == "Brunsviga":
                    sources.append(BrunsvigaScraper())
                elif name == "DieRegion":
                    sources.append(DieRegionScraper())
                elif name == "Blau-Wal Kultur":
                    sources.append(BlauWalScraper())
                elif name == "Barnaby's Blues Bar":
                    sources.append(BarnabysScraper())
                elif name == "Komödie am Altstadtmarkt":
                    sources.append(KomoedieScraper())
                elif name == "Staatstheater Braunschweig":
                    sources.append(StaatstheaterScraper())
                elif name == "Braunschweig Lions":
                    sources.append(LionsScraper())
                elif name == "KufA Haus":
                    sources.append(KufaScraper())
                elif name == "Westand":
                    sources.append(WestandScraper())
                elif name == "3 Landesmuseen":
                    sources.append(LandesmuseenScraper())
                elif name == "Eventbrite Braunschweig":
                    sources.append(EventbriteScraper())
                elif name == "Basketball Löwen":
                    sources.append(LoewenScraper())
                elif name == "VHS Braunschweig":
                    sources.append(VHSScraper())
                else:
                    sources.append(GenericWebScraper(name, s.get("url")))
    except Exception as e:
        log_callback(f"[ERROR] Failed to load sources from config: {e}")
        
    return sources

def get_all_scrapers(config_file="config.json"):
    """Returns a list of all scraper names defined in the config."""
    if not os.path.exists(config_file):
        return []
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [s.get("name") for s in data.get("sources", []) if s.get("name")]
    except Exception:
        return []

def run_pipeline(log_callback=print, event_callback=None, progress_callback=None, model_name="qwen2.5-coder:7b", stop_event=None, enabled_scrapers=None):
    print("DEBUG: Inside run_pipeline...")
    if progress_callback: progress_callback({"phase": "init", "percent": 0, "detail": "Lade Konfiguration..."})
    log_callback("=== Braunschweig Event Calendar Automation ===")
    
    print("DEBUG: Calling load_sources_from_config...")
    sources = load_sources_from_config(log_callback=log_callback, enabled_scrapers=enabled_scrapers)
    
    if enabled_scrapers is not None:
        log_callback(f"Filter aktiv: Nutze {len(sources)} von {len(get_all_scrapers())} verfügbaren Quellen.")
        
    print("DEBUG: Finished load_sources_from_config...")
    if not sources:
        log_callback("No active sources found in config.json. Please enable some and try again.")
        return
    
    log_callback(f"Loaded {len(sources)} active sources to scrape.")
    
    # 1. Scrape all raw text
    all_raw_text = []
    total_sources = len(sources)
    for i, source in enumerate(sources):
        if stop_event and stop_event.is_set():
            log_callback("Abbruch: Scraper-Phase wurde gestoppt.")
            return []
        if progress_callback: progress_callback({"phase": "scraping", "percent": int((i/total_sources)*30), "detail": f"Scrape Website {i+1}/{total_sources}: {source.name}"})
        try:
            log_callback(f"[START] Scraping text from target: {source.name}...")
            text = source.scrape_events_text()
            if text:
                all_raw_text.append((source.name, text))
                log_callback(f"[SUCCESS] Scraped {len(text)} characters from {source.name}.")
            else:
                log_callback(f"[WARN] No text could be extracted from {source.name}.")
        except Exception as e:
            log_callback(f"[ERROR] Error gathering text from {source.name}: {e}")
            
    # 2. Extract Event JSON via Local LLM
    log_callback("\nStarting LLM Extraction via Qwen and Instructor...")
    parser = LLMEventParser(model_name=model_name)
    parsed_events = []
    
    # Build a map of source name -> URL for linking
    source_urls = {}
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for s in cfg.get("sources", []):
            source_urls[s.get("name", "")] = s.get("url", "")
    except Exception:
        pass
    
    if all_raw_text:
        total_texts = len(all_raw_text)
        for idx, (source_name, text_block) in enumerate(all_raw_text):
            if stop_event and stop_event.is_set():
                log_callback("Abbruch: KI-Analyse-Phase wurde gestoppt.")
                return parsed_events
            if progress_callback: progress_callback({"phase": "llm", "percent": 30 + int((idx/total_texts)*60), "detail": f"KI Analyse {idx+1}/{total_texts}: {source_name} (Bitte Geduld...)"})
            log_callback(f"\n[START] Parsing source {idx+1}/{total_texts}: {source_name}...")
            formatted_block = f"--- START SITE: {source_name} ---\n{text_block}\n--- END SITE: {source_name} ---"
            
            try:
                events = parser.parse_events(formatted_block)
                if events:
                    # Attach source URL to each event
                    source_url = source_urls.get(source_name, "")
                    for ev in events:
                        log_callback(f"  Event found: {ev['title']} ({ev['date']})")
                        ev["source_url"] = source_url
                        ev["source_name"] = source_name
                    parsed_events.extend(events)
                    log_callback(f"[SUCCESS] Extracted {len(events)} events from {source_name}.")
                    if event_callback:
                        event_callback(events)
                else:
                    log_callback(f"[INFO] No valid events found for {source_name}.")
            except Exception as e:
                log_callback(f"[ERROR] Failed to parse events for {source_name}: {e}")
    else:
        log_callback("[WARN] No raw text was gathered. Skipping LLM execution.")
    
    log_callback(f"\n=== LLM Extraction Complete ===")
    log_callback(f"Total events extracted: {len(parsed_events)}")
    log_callback("Warte auf Review im Dashboard...")
    
    if progress_callback: progress_callback({"phase": "review", "percent": 90, "detail": "Bitte Events im Feed überprüfen und bestätigen."})
    
    return parsed_events

def build_ics_from_events(events, log_callback=print):
    """Build ICS calendar files from a list of event dicts. Called after user review."""
    if events:
        log_callback("Building ICS Calendars...")
        builder = ICSBuilder()
        # Remove extra keys that ICS builder doesn't need
        clean_events = []
        for ev in events:
            clean = {k: v for k, v in ev.items() if k not in ("source_url", "source_name")}
            clean_events.append(clean)
        builder.build_calendars(clean_events)
        log_callback(f"Done! {len(clean_events)} events in ICS-Dateien geschrieben.")
    else:
        log_callback("No events to build calendars from.")

def main():
    run_pipeline(log_callback=print)

if __name__ == "__main__":
    main()
