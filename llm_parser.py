from pydantic import BaseModel, Field, field_validator
from typing import Literal, List
import instructor
from openai import OpenAI
from datetime import datetime, date

class Event(BaseModel):
    title: str
    date: str = Field(description="Format YYYY-MM-DD")
    time: str = Field(description="Format HH:MM")
    location: str
    category: Literal["party", "kultur", "musik", "theater", "sonstiges"]
    description: str = Field(description="Short summary")

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if not isinstance(v, str):
            return "sonstiges"
        v = v.lower().strip()
        if any(kw in v for kw in ["party", "disco", "club", "tanz"]): return "party"
        if any(kw in v for kw in ["theater", "comedy", "kabarett", "oper", "musical", "schauspiel", "bühne", "hypnose"]): return "theater"
        if any(kw in v for kw in ["musik", "konzert", "live", "band", "tribute", "show"]): return "musik"
        if any(kw in v for kw in ["kultur", "ausstellung", "lesung", "vortrag", "museum", "führung", "markt", "messe", "slam", "leseflair"]): return "kultur"
        return "sonstiges"

class EventList(BaseModel):
    events: List[Event]

class LLMEventParser:
    def __init__(self, model_name="mistral-nemo", api_url="http://127.0.0.1:11434/v1", api_key="ollama"):
        self.model_name = model_name
        self.api_url = api_url
        self.api_key = api_key
        
        self.client = instructor.from_openai(
            OpenAI(
                base_url=self.api_url,
                api_key=self.api_key, 
                timeout=240.0,    # 4 minute total timeout
                default_headers={
                    "HTTP-Referer": "http://localhost:8081", # Required for OpenRouter
                    "X-Title": "Braunschweig-Events Scraper",
                }
            ),
            mode=instructor.Mode.TOOLS,
        )

    def _build_system_prompt(self) -> str:
        today_str = date.today().isoformat()
        return f'''Du bist ein Experte für strukturierte Datenextraktion aus deutschsprachigen Veranstaltungswebseiten.
Heute ist der {today_str}.

AUFGABE: Extrahiere ALLE kommenden Veranstaltungen (ab heute) aus dem gegebenen Text.

REGELN:
1. DATUMS-FORMAT: Jedes Event MUSS ein Datum im Format YYYY-MM-DD haben.
2. RELATIVE DATEN: Übersetze Begriffe wie "heute", "morgen", "dieses Wochenende" IMMER in das konkrete Datum basierend auf heute ({today_str}). Beispiel: Wenn heute 2026-03-18 ist, wird "heute" zu 2026-03-18.
3. JAHR: Wenn kein Jahr angegeben ist, verwende 2026.
4. FILTER: Ignoriere vergangene Events (vor {today_str}).
5. STANDARD-ZEIT: Wenn keine Uhrzeit angegeben ist, verwende "20:00".
6. KATEGORIEN: Verwende EXAKT eines der folgenden Literale:
   - "party" = Clubnächte, Ü30/Ü40, Tanzparties
   - "musik" = Konzerte, Live-Bands, Tribute Shows (KEINE Comedy!)
   - "theater" = Theater, Comedy, Kabarett, Musical, Stand-Up
   - "kultur" = Ausstellungen, Märkte, Lesungen, Workshops, Museen, Führungen
   - "sonstiges" = Alles andere
7. ORT (location): Enthalte den tatsächlichen Veranstaltungsort (z.B. "Brunsviga", "381", "Westand").
8. BESCHREIBUNG: Kurz und informativ (max. 1 Satz).
9. SPRACHE: Beschreibe das Event auf Deutsch.
10. REPETITIVE EVENTS: Oft enthalten Webseiten lange Listen mit sehr ähnlichen Terminen (z.B. eine Comedy-Show an 10 verschiedenen Daten). Du MUSST JEDEN einzelnen Termin als eigenes Event extrahieren. Höre niemals in der Mitte auf, auch wenn sich die Titel oder Orte wiederholen.

WICHTIG: Sei absolut gründlich! Dein Ziel ist eine Vollständigkeit von 100%. Überspringe KEIN Event, das ein erkennbares Datum hat.'''

    def _extract_from_chunk(self, text_chunk: str, chunk_index: int = 0, total_chunks: int = 0) -> list:
        """Send a single text chunk to the LLM and extract events."""
        if total_chunks > 1:
            print(f"  [KI] Verarbeite Abschnitt {chunk_index + 1}/{total_chunks} ({len(text_chunk)} Zeichen)...")
            
        try:
            resp: EventList = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": self._build_system_prompt()},
                    {"role": "user", "content": f"Extrahiere alle Events aus diesem Text:\n\n{text_chunk}"}
                ],
                response_model=EventList,
                max_retries=1,
                temperature=0,
                timeout=180.0, # Increased for 12B/14B models on consumer GPUs
            )
            return resp.events
        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower():
                print(f"  [LLM-Timeout] Abschnitt {chunk_index + 1} dauerte zu lange (180s). Überspringe.")
            else:
                print(f"  [LLM-Error] Abschnitt {chunk_index + 1}: {e}")
            return []

    def parse_events(self, raw_text: str) -> list:
        """Parses events from raw text, splitting into chunks if text is long."""
        today = date.today()
        
        # Adaptive chunk size based on model
        # Larger chunks for small models (fast), smaller chunks for big models (quality/VRAM)
        m_lower = self.model_name.lower()
        if "12b" in m_lower or "14b" in m_lower or "nemo" in m_lower or "deepseek" in m_lower:
            chunk_size = 1800  # Smaller chunks for high quality & VRAM protection
        elif "7b" in m_lower:
            chunk_size = 2500
        elif "1b" in m_lower or "3b" in m_lower or "4b" in m_lower:
            chunk_size = 2000  # Smaller models struggle with long context, so give them less at once
        else:
            chunk_size = 2500
            
        overlap = 500 # Ensure events split across line boundaries are not lost
        chunks = self._split_into_chunks(raw_text, chunk_size, overlap)
        
        all_events = []
        for i, chunk in enumerate(chunks):
            events = self._extract_from_chunk(chunk, i, len(chunks))
            all_events.extend(events)
        
        # Post-processing: filter past events + deduplicate
        valid_events = []
        seen = set()
        
        for event in all_events:
            try:
                # Basic validation: must have title and date
                if not event.title or not event.date:
                    continue
                
                # Robust date parsing
                raw_date = event.date.strip()
                event_date = None
                
                # Check different common formats
                for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y"]:
                    try:
                        event_date = datetime.strptime(raw_date, fmt).date()
                        break
                    except ValueError:
                        continue
                
                if event_date is None:
                    print(f"[LLM Parser] [WARN] Could not parse date format: {raw_date}")
                    continue
                    
                if event_date < today:
                    continue
                    
                # Use title, date and time as dedup key (time added for multiday events)
                dedup_key = f"{event.title.lower().strip()}-{event.date}-{event.time}"
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)
                
                valid_events.append(event.model_dump())
            except (ValueError, AttributeError):
                continue
        
        return valid_events

    def _split_into_chunks(self, text: str, max_chars: int, overlap: int) -> list:
        """Split text into overlapping chunks at line boundaries."""
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        lines = text.split('\n')
        current_chunk = []
        current_size = 0
        
        for i, line in enumerate(lines):
            line_len = len(line) + 1
            
            if current_size + line_len > max_chars and current_chunk:
                # Record this chunk
                chunk_text = '\n'.join(current_chunk)
                chunks.append(chunk_text)
                
                # Backtrack for overlap
                # Find how many previous lines fit into the 'overlap' window
                overlap_lines = []
                overlap_size = 0
                for back_line in reversed(current_chunk):
                    if overlap_size + len(back_line) + 1 > overlap:
                        break
                    overlap_lines.insert(0, back_line)
                    overlap_size += len(back_line) + 1
                
                current_chunk = overlap_lines + [line]
                current_size = overlap_size + line_len
            else:
                current_chunk.append(line)
                current_size += line_len
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
