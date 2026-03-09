import os
from datetime import datetime, timezone
import uuid

class ICSBuilder:
    def __init__(self, output_dir="output"):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
    def _create_base_calendar(self, name: str) -> list:
        return [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            f"PRODID:-//Braunschweig Events//{name.capitalize()}",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            f"X-WR-CALNAME:Braunschweig {name.capitalize()}",
            "X-WR-TIMEZONE:Europe/Berlin",
            f"X-WR-CALDESC:Kommende {name.capitalize()} Events"
        ]

    def build_calendars(self, all_events: list):
        """Takes a list of JSON event objects and distributes them into .ics files based on category."""
        
        # Group events by category
        categorized = {
            "party": [],
            "kultur": [],
            "musik": [],
            "theater": [],
            "sonstiges": []
        }
        
        for ev in all_events:
            cat = ev.get("category", "sonstiges").lower()
            if cat not in categorized:
                cat = "sonstiges"
            categorized[cat].append(ev)
            
        dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        seen_events = set()
        
        for category, events in categorized.items():
            if not events:
                continue
                
            lines = self._create_base_calendar(category)
            
            for ev in events:
                try:
                    title = ev.get("title", "Event").replace(",", "\\,").replace(";", "\\;")
                    date_str = ev.get("date", "")
                    time_str = ev.get("time", "00:00")
                    desc = ev.get("description", "").replace("\n", "\\n").replace(",", "\\,").replace(";", "\\;")
                    location = ev.get("location", "").replace(",", "\\,").replace(";", "\\;")
                    
                    if not date_str:
                        continue # Skip if no date
                        
                    # Global duplicate prevention key (case-insensitive title + date)
                    dedup_key = f"{title.lower().strip()}-{date_str}"
                    if dedup_key in seen_events:
                        print(f"Skipping duplicate event: {title} on {date_str}")
                        continue
                    seen_events.add(dedup_key)
                        
                    # Parse start datetime
                    start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                    start_format = start_dt.strftime("%Y%m%dT%H%M%S")
                    
                    # Ensure unique ID based on title and date to prevent massive duplicates on next run
                    unique_str = f"{title}-{date_str}".encode('utf-8')
                    event_id = str(uuid.uuid5(uuid.NAMESPACE_URL, unique_str.decode('utf-8')))
                    uid = f"{event_id}@bs-events.de"
                    
                    lines.extend([
                        "BEGIN:VEVENT",
                        f"UID:{uid}",
                        f"DTSTAMP:{dtstamp}",
                        f"DTSTART;TZID=Europe/Berlin:{start_format}",
                        f"SUMMARY:{title}",
                        f"DESCRIPTION:{desc}",
                        f"LOCATION:{location}",
                        "END:VEVENT"
                    ])
                except Exception as e:
                    print(f"Skipping an event in {category} due to parsing error: {e}")
            
            lines.append("END:VCALENDAR")
            
            filename = os.path.join(self.output_dir, f"{category}.ics")
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
                
            print(f"[{category}] Generated {len(events)} events in {filename}")
