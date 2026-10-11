"""Scraper for Facebook Marketplace."""

import re
from typing import List, Optional
from urllib.parse import quote
from base_scraper import BaseScraper
from models import CarListing


class FacebookMarketplaceScraper(BaseScraper):
    """Scraper for Facebook Marketplace car listings."""
    
    def __init__(self):
        """Initialize the Facebook Marketplace scraper."""
        super().__init__()
        self.base_url = "https://www.facebook.com/marketplace"
    
    def get_source_name(self) -> str:
        """Return the name of the source website."""
        return "Facebook Marketplace"
    
    def search(self, make: str, model: str, location: str = None) -> List[CarListing]:
        """
        Search for car listings on Facebook Marketplace.
        
        Note: Facebook Marketplace heavily relies on JavaScript rendering,
        which makes it difficult to scrape with simple requests.
        This is a simplified implementation that shows the structure.
        
        For production use, you would need:
        1. Selenium or Playwright for JavaScript rendering
        2. Proper authentication handling
        3. More robust error handling
        
        Args:
            make: Car make
            model: Car model
            location: Optional location
            
        Returns:
            List of CarListing objects (may be empty due to JavaScript requirements)
        """
        listings = []
        
        search_query = f"{make} {model}"
        encoded_query = quote(search_query)
        
        # Facebook Marketplace URL structure for vehicles
        url = f"{self.base_url}/category/vehicles?query={encoded_query}"
        
        print(f"Searching Facebook Marketplace: {url}")
        print("Note: Facebook Marketplace may require login; parsing is best-effort.")
        
        # Attempt basic fetch (will likely return minimal data)
        soup = self.fetch_page(url, 'a[href*="/marketplace/item/"]')
        if not soup:
            print("Unable to fetch Facebook Marketplace (JavaScript required)")
            return listings
        
        # Try to find listings (unlikely to work without JS rendering)
        listing_items = soup.find_all('div', {'class': lambda x: x and 'marketplace' in str(x).lower()})
        
        for item in listing_items[:10]:
            try:
                listing = self._parse_listing(item, make, model)
                if listing:
                    listings.append(listing)
            except Exception as e:
                print(f"Error parsing Facebook listing: {e}")
                continue
        
        if len(listings) == 0:
            print("Facebook Marketplace returned no results (JavaScript rendering required)")
        else:
            print(f"Found {len(listings)} listings on Facebook Marketplace")
        
        return listings
    
    def _parse_listing(self, item, make: str, model: str) -> Optional[CarListing]:
        """
        Parse a single listing item.
        
        Args:
            item: BeautifulSoup element containing listing data
            make: Car make
            model: Car model
            
        Returns:
            CarListing object or None if parsing fails
        """
        # This is a placeholder implementation
        # Facebook's actual structure would need to be analyzed
        
        title_elem = item.find('span')
        if not title_elem:
            return None
        
        title = title_elem.get_text(strip=True)
        
        link_elem = item.find('a')
        url = link_elem.get('href', '') if link_elem else ""
        if url and not url.startswith('http'):
            url = self.base_url + url
        
        return CarListing(
            title=title,
            price="See listing",
            year=self._extract_year(title),
            make=make,
            model=model,
            mileage=None,
            location=None,
            url=url,
            source=self.get_source_name()
        )
    
    def _extract_year(self, text: str) -> str:
        """Extract year from text."""
        match = re.search(r'\b(19\d{2}|20\d{2})\b', text)
        return match.group(1) if match else None
