import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

class EventScraper:
    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url

    def fetch_html(self, url: str) -> str:
        """Fetches the HTML content using headless Playwright to render JavaScript."""
        print(f"[{self.name}] Booting Playwright browser for {url}...")
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    ignore_https_errors=True,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                # Go to page and wait for a bit of network idle
                page.goto(url, wait_until="networkidle", timeout=30000)
                
                # Extra explicit wait for slow frameworks
                time.sleep(3)
                
                # If there is an iframe (like Brain Klub uses sometimes or embedded tickets) evaluate inside it too
                # Try to scroll down to trigger lazy loading
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                
                html = page.content()
                browser.close()
                return html
        except Exception as e:
            print(f"[{self.name}] Error rendering {url} with Playwright: {e}")
            return ""

    def clean_html_to_text(self, html: str) -> str:
        """Converts HTML to plain text, stripping out scripts and styles to send to the LLM."""
        if not html:
            return ""
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.extract()
            
        # Get text
        text = soup.get_text(separator='\n')
        
        # Collapse multiple newlines/spaces
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        with open(f"/tmp/debug_{self.name.replace(' ', '_')}.txt", "w", encoding="utf-8") as f:
             f.write(text)
             
        return text

    def scrape_events_text(self) -> str:
        """To be overridden by subclasses. Should return a large chunk of text containing event informations."""
        raise NotImplementedError("Subclasses must implement scrape_events_text")
