import json
import requests
import re

class LLMEventParser:
    def __init__(self, model_name="hf.co/chatpdflocal/Qwen2.5.1-Coder-14B-Instruct-GGUF:Q4_K_M", api_url="http://127.0.0.1:11434/api/generate"):
        self.model_name = model_name
        self.api_url = api_url

    def parse_events(self, raw_text: str) -> list:
        """Sends raw text to the local LLM and asks for a structured JSON response."""
        
        system_prompt = '''You are an expert data extraction AI.
        I will give you raw text scraped from an event website in Braunschweig.
        Your job is to extract all upcoming events and return them EXACTLY as a JSON array of objects.
        Do NOT output any other text, markdown formatting, or explanations. Just the JSON.
        
        The JSON MUST follow this exact schema:
        [
          {
            "title": "Name of the event",
            "date": "YYYY-MM-DD",
            "time": "HH:MM",
            "location": "Name of the venue",
            "category": "party" (Must be one of: party, kultur, musik, theater, sonstiges),
            "description": "Short summary"
          }
        ]
        
        If no events are found, return exactly: []
        '''
        
        # We might need to truncate raw_text if it's too large for the context window
        max_chars = 15000 
        if len(raw_text) > max_chars:
            raw_text = str(raw_text)[:max_chars]
            
        prompt = f"{system_prompt}\n\nRAW TEXT:\n{raw_text}\n\nJSON OUTPUT:"
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            print(f"Sending request to {self.model_name} (this might take a moment depending on your GPU/CPU)...")
            response = requests.post(self.api_url, json=payload, timeout=600)
            response.raise_for_status()
            
            result_json = response.json()
            response_text = result_json.get("response", "").strip()
            
            print(f"---\nRAW LLM OUTPUT:\n{response_text[:500]}...\n---")
            
            try:
                # First try direct JSON parsing in case it correctly returned an array
                parsed = json.loads(response_text)
                if isinstance(parsed, list):
                    return parsed
                elif isinstance(parsed, dict) and "events" in parsed:
                     # sometimes models wrap the array in an object
                     return parsed["events"]
            except json.JSONDecodeError:
                pass

            # Fallback: Use regex to find the JSON array in case there is trailing/leading text or markdown blocks
            response_text = re.sub(r'```json\s*', '', response_text)
            response_text = re.sub(r'```\s*', '', response_text)
            
            match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if match:
                clean_json = match.group(0)
                try:
                    events = json.loads(clean_json)
                    return events
                except json.JSONDecodeError:
                    print("Could not find a valid JSON array in model output.")
                    return []
            else:
                 print("Could not find a valid JSON array in model output.")
                 return []
            
        except Exception as e:
            print(f"Error communicating with local LLM or parsing output: {e}")
            return []
