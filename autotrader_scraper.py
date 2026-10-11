"""Scraper for AutoTrader.ca."""

import re
from typing import List, Optional
from urllib.parse import quote
from base_scraper import BaseScraper
from models import CarListing


class AutoTraderScraper(BaseScraper):
    """Scraper for AutoTrader.ca car listings."""
    
    def __init__(self):
        """Initialize the AutoTrader scraper."""
        super().__init__()
        self.base_url = "https://www.autotrader.ca"
    
    def get_source_name(self) -> str:
        """Return the name of the source website."""
        return "AutoTrader"
    
    def search(self, make: str, model: str, location: str = None) -> List[CarListing]:
        """
        Search for car listings on AutoTrader.
        
        Args:
            make: Car make
            model: Car model
            location: Optional location
            
        Returns:
            List of CarListing objects
        """
        listings = []
        
        # Build AutoTrader search URL
        # Format: /cars/{make}/{model}/
        make_clean = make.lower().replace(" ", "-")
        model_clean = model.lower().replace(" ", "-")
        
        url = f"{self.base_url}/cars/{make_clean}/{model_clean}/"
        
        print(f"Searching AutoTrader: {url}")
        
        soup = self.fetch_page(url, '.result-item, .listing-item')
        if not soup:
            return listings
        
        # Find all listing containers
        # AutoTrader uses specific class names for listings
        listing_items = soup.select('.result-item, .listing-item')
        
        if not listing_items:
            # Try alternative selectors
            listing_items = soup.find_all('div', {'class': lambda x: x and 'listing' in str(x).lower()})
        
        for item in listing_items[:20]:  # Limit to first 20 results
            try:
                listing = self._parse_listing(item, make, model)
                if listing:
                    listings.append(listing)
            except Exception as e:
                print(f"Error parsing AutoTrader listing: {e}")
                continue
        
        print(f"Found {len(listings)} listings on AutoTrader")
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
        # Extract title/link
        title_elem = item.find('a', class_='result-title')
        if not title_elem:
            title_elem = item.find('a')
        
        if not title_elem:
            return None
        
        title = title_elem.get_text(strip=True)
        url = title_elem.get('href', '')
        if url and not url.startswith('http'):
            url = self.base_url + url
        
        # Extract price
        price_elem = item.find('span', class_='price-amount')
        if not price_elem:
            price_elem = item.find('div', {'class': lambda x: x and 'price' in str(x).lower()})
        price = price_elem.get_text(strip=True) if price_elem else "Contact for price"
        
        # Extract year
        year_elem = item.find('span', class_='year')
        year = year_elem.get_text(strip=True) if year_elem else self._extract_year(title)
        
        # Extract mileage
        mileage_elem = item.find('span', class_='kms')
        if not mileage_elem:
            mileage_elem = item.find('div', {'class': lambda x: x and 'mileage' in str(x).lower()})
        mileage = mileage_elem.get_text(strip=True) if mileage_elem else None
        
        # Extract location
        location_elem = item.find('span', class_='location')
        if not location_elem:
            location_elem = item.find('div', {'class': lambda x: x and 'location' in str(x).lower()})
        location = location_elem.get_text(strip=True) if location_elem else None
        
        return CarListing(
            title=title,
            price=price,
            year=year,
            make=make,
            model=model,
            mileage=mileage,
            location=location,
            url=url,
            source=self.get_source_name()
        )
    
    def _extract_year(self, text: str) -> str:
        """Extract year from text."""
        match = re.search(r'\b(19\d{2}|20\d{2})\b', text)
        return match.group(1) if match else None
