import json
from llm_parser import LLMEventParser

text = """
Willkommen auf der Seite des Stereowerk.
Am 14. Oktober 2026 findet bei uns die "80er Jahre Kultparty" statt. 
Beginn ist um 22:30 Uhr.
Am 16.10.2026 haben wir außerdem das "Indie Rock Festival" ab 20:00 Uhr.
Wir freuen uns auf euch!
"""

parser = LLMEventParser(model_name="hf.co/chatpdflocal/Qwen2.5.1-Coder-14B-Instruct-GGUF:Q4_K_M")
events = parser.parse_events(text)

print("Extracted Events:")
print(json.dumps(events, indent=2))
