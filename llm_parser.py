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
    def __init__(self, model_name="qwen2.5-coder:7b", api_url="http://127.0.0.1:11434/v1"):
        self.model_name = model_name
        self.api_url = api_url
        
        # Initialize instructor with the OpenAI compatible Ollama endpoint
        self.client = instructor.from_openai(
            OpenAI(
                base_url=self.api_url,
                api_key="ollama", # required by library but arbitrary for local Ollama
                timeout=120.0,    # 2 minute timeout for long inferences
            ),
            mode=instructor.Mode.JSON,
        )

    def _build_system_prompt(self) -> str:
        today_str = date.today().isoformat()
        return f'''Du bist ein Experte für strukturierte Datenextraktion aus deutschsprachigen Veranstaltungswebseiten.
Heute ist der {today_str}.

AUFGABE: Extrahiere ALLE kommenden Veranstaltungen (ab heute) aus dem gegebenen Text.

REGELN:
1. Jedes Event MUSS ein gültiges Datum im Format YYYY-MM-DD haben. Wenn kein Jahr angegeben ist, verwende 2026.
2. Ignoriere vergangene Events (vor {today_str}).
3. Wenn keine Uhrzeit angegeben ist, verwende "20:00" als Standardwert.
4. Kategorisiere jedes Event als GENAU EINE der folgenden Kategorien:
   - "party" = Clubnächte, DJ Sets, Tanzveranstaltungen, Ü30/Ü40/Ü60 Partys
   - "musik" = Konzerte, Live-Musik, Tribute Shows, Bands
   - "theater" = Theater, Schauspiel, Oper, Musical, Ballett, Kabarett, Comedy
   - "kultur" = Ausstellungen, Lesungen, Vorträge, Museen, Workshops, Führungen, Märkte, Messen
   - "sonstiges" = Sport, Kinder-Events, alles andere
5. Der Ort (location) MUSS den tatsächlichen Veranstaltungsort enthalten (z.B. "Brunsviga", "Westand", "Staatstheater"). Wenn der Text von einer spezifischen Seite kommt, ist das meistens der Ort.
6. Die Beschreibung soll kurz und informativ sein (max 1 Satz).
7. Extrahiere JEDEN einzelnen Termin als separates Event, auch wenn mehrere am gleichen Tag stattfinden.
8. Wenn der Text keine gültigen Events enthält, gib eine leere Liste zurück.

WICHTIG: Sei gründlich! Überspringe KEIN Event, das ein erkennbares Datum hat.'''

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
                max_retries=1, # Reduced retries to avoid long hangs
                temperature=0,
                timeout=90.0, # Explicit timeout for the inference
            )
            return resp.events
        except Exception as e:
            # Check specifically for timeout
            if "timeout" in str(e).lower():
                print(f"  [LLM-Timeout] Abschnitt {chunk_index + 1} dauerte zu lange (90s). Überspringe.")
            else:
                print(f"  [LLM-Chunk-Error] Abschnitt {chunk_index + 1}: {e}")
            return []

    def parse_events(self, raw_text: str) -> list:
        """Parses events from raw text, splitting into chunks if text is long."""
        today = date.today()
        
        # Split into chunks of ~3500 chars at line boundaries
        chunk_size = 3500
        chunks = self._split_into_chunks(raw_text, chunk_size)
        
        print(f"Sending {len(chunks)} chunk(s) to {self.model_name} via Instructor...")
        
        all_events = []
        for i, chunk in enumerate(chunks):
            # Diagnostic: print first few chars to identify what's being sent
            preview = chunk[:200].replace('\n', ' ')
            print(f"  [DEBUG] Chunk Preview: {preview}...")
            
            events = self._extract_from_chunk(chunk, i, len(chunks))
            all_events.extend(events)
        
        # Post-processing: filter past events + deduplicate
        valid_events = []
        seen = set()
        
        for event in all_events:
            try:
                event_date = datetime.strptime(event.date, "%Y-%m-%d").date()
                if event_date < today:
                    print(f"  Filtered out past event: {event.title} ({event.date})")
                    continue
                    
                # Deduplicate by title + date (case-insensitive)
                dedup_key = f"{event.title.lower().strip()}-{event.date}"
                if dedup_key in seen:
                    print(f"  Filtered out duplicate: {event.title} ({event.date})")
                    continue
                seen.add(dedup_key)
                
                valid_events.append(event.model_dump())
            except ValueError:
                print(f"  Filtered out event with invalid date: {event.title} ({event.date})")
        
        return valid_events

    def _split_into_chunks(self, text: str, max_chars: int) -> list:
        """Split text into chunks at line boundaries, respecting max_chars."""
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        lines = text.split('\n')
        current_chunk = []
        current_size = 0
        
        for line in lines:
            line_len = len(line) + 1  # +1 for newline
            if current_size + line_len > max_chars and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                current_size = 0
            current_chunk.append(line)
            current_size += line_len
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
