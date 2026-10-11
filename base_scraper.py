"""Base scraper class with common functionality."""

from abc import ABC, abstractmethod
from typing import List, Optional
import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import time

from models import CarListing


class BaseScraper(ABC):
    """Abstract base class for all car listing scrapers."""
    
    def __init__(self):
        """Initialize the scraper with common settings."""
        load_dotenv()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.timeout = 10
        self.last_error = None
        
    @abstractmethod
    def search(self, make: str, model: str, location: str = None) -> List[CarListing]:
        """
        Search for car listings.
        
        Args:
            make: Car make (e.g., 'Honda', 'Toyota')
            model: Car model (e.g., 'Civic', 'Camry')
            location: Optional location filter
            
        Returns:
            List of CarListing objects
        """
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return the name of the source website."""
        pass
    
    def fetch_page(self, url: str, wait_selector: str = None) -> Optional[BeautifulSoup]:
        """
        Fetch and parse a webpage.
        
        Args:
            url: URL to fetch
            
        Returns:
            BeautifulSoup object of the parsed page
        """
        self.last_error = None
        if os.getenv('SCRAPER_BACKEND', 'requests').lower() == 'playwright':
            return self._fetch_rendered_page(url, wait_selector)
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.RequestException as e:
            self.last_error = type(e).__name__
            print(f"Error fetching {url}: {e}")
            return None

    def _fetch_rendered_page(self, url: str, wait_selector: str) -> Optional[BeautifulSoup]:
        """Render a page in a browser before passing it to the existing parser."""
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                options = {'headless': os.getenv('PLAYWRIGHT_HEADLESS', 'true').lower() != 'false'}
                proxy_server = os.getenv('SCRAPER_PROXY_SERVER')
                if proxy_server:
                    options['proxy'] = {'server': proxy_server}
                    for credential in ('username', 'password'):
                        value = os.getenv(f'SCRAPER_PROXY_{credential.upper()}')
                        if value:
                            options['proxy'][credential] = value
                browser = playwright.chromium.launch(**options)
                try:
                    page = browser.new_page()
                    page.set_default_timeout(int(os.getenv('SCRAPER_TIMEOUT_MS', '30000')))
                    response = page.goto(url, wait_until='domcontentloaded')
                    if response and response.status >= 400:
                        self.last_error = f'HTTP {response.status}'
                        print(f"HTTP {response.status} fetching {url}")
                        return None
                    if wait_selector:
                        page.wait_for_selector(wait_selector, state='attached')
                    return BeautifulSoup(page.content(), 'html.parser')
                finally:
                    browser.close()
        except Exception as error:
            self.last_error = type(error).__name__
            print(f"Browser fetch failed for {url} ({type(error).__name__}). Check browser installation, selectors, and site access.")
            return None
    
    def delay(self, seconds: float = 1.0):
        """Add delay between requests to be respectful to servers."""
        time.sleep(seconds)
