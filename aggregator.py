"""Main aggregator class that combines results from all scrapers."""

from typing import List
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from models import CarListing
from kijiji_scraper import KijijiScraper
from autotrader_scraper import AutoTraderScraper
from facebook_scraper import FacebookMarketplaceScraper
from conexion import ListingStore


class CarFinderAggregator:
    """Aggregates car listings from multiple sources."""
    
    def __init__(self, sources=None):
        """Initialize the aggregator with all available scrapers."""
        available = {
            'kijiji': KijijiScraper,
            'autotrader': AutoTraderScraper,
            'facebook': FacebookMarketplaceScraper,
        }
        selected = sources if sources is not None else list(available)
        if not selected or any(source not in available for source in selected):
            raise ValueError('Choose sources from kijiji, autotrader, facebook.')
        self.scrapers = [available[source]() for source in dict.fromkeys(selected)]
        self.store = ListingStore() if os.getenv('DATABASE_URL') else None
    
    def search(self, make: str, model: str, location: str = None, 
               parallel: bool = True) -> List[CarListing]:
        """
        Search for car listings across all sources.
        
        Args:
            make: Car make (e.g., 'Honda', 'Toyota')
            model: Car model (e.g., 'Civic', 'Camry')
            location: Optional location filter
            parallel: Whether to run scrapers in parallel (default: True)
            
        Returns:
            Combined list of CarListing objects from all sources
        """
        all_listings = []
        failed_sources = 0
        
        print(f"\n{'='*60}")
        print(f"Searching for: {make} {model}")
        if location:
            print(f"Location: {location}")
        print(f"{'='*60}\n")
        
        if parallel:
            # Run scrapers in parallel for faster results
            with ThreadPoolExecutor(max_workers=len(self.scrapers)) as executor:
                future_to_scraper = {
                    executor.submit(scraper.search, make, model, location): scraper
                    for scraper in self.scrapers
                }
                
                for future in as_completed(future_to_scraper):
                    scraper = future_to_scraper[future]
                    try:
                        listings = future.result()
                        if scraper.last_error:
                            raise RuntimeError(scraper.last_error)
                        # Update make and model for listings that don't have them
                        for listing in listings:
                            if not listing.make:
                                listing.make = make
                            if not listing.model:
                                listing.model = model
                        all_listings.extend(listings)
                    except Exception as e:
                        failed_sources += 1
                        print(f"Error with {scraper.get_source_name()}: {e}")
        else:
            # Run scrapers sequentially
            for scraper in self.scrapers:
                try:
                    print(f"\nSearching {scraper.get_source_name()}...")
                    listings = scraper.search(make, model, location)
                    if scraper.last_error:
                        raise RuntimeError(scraper.last_error)
                    # Update make and model for listings that don't have them
                    for listing in listings:
                        if not listing.make:
                            listing.make = make
                        if not listing.model:
                            listing.model = model
                    all_listings.extend(listings)
                except Exception as e:
                    failed_sources += 1
                    print(f"Error with {scraper.get_source_name()}: {e}")
        
        if failed_sources == len(self.scrapers):
            raise RuntimeError('All selected sources failed. Check site access, selectors, and browser configuration.')
        unique_listings = {}
        for listing in all_listings:
            key = (listing.source, listing.external_id or listing.url)
            unique_listings[key] = listing
        all_listings = list(unique_listings.values())
        if self.store:
            self.store.save(all_listings)
        return all_listings
    
    def search_and_display(self, make: str, model: str, location: str = None,
                           parallel: bool = True):
        """
        Search and display results in a formatted way.
        
        Args:
            make: Car make
            model: Car model
            location: Optional location filter
        """
        listings = self.search(make, model, location, parallel=parallel)
        
        print(f"\n{'='*60}")
        print(f"SEARCH RESULTS: Found {len(listings)} total listings")
        print(f"{'='*60}")
        
        if not listings:
            print("\nNo listings found. This could be because:")
            print("1. No matching vehicles are available")
            print("2. The websites require JavaScript rendering (especially Facebook)")
            print("3. The website structure has changed and scrapers need updating")
            return
        
        # Group by source for organized display
        by_source = {}
        for listing in listings:
            source = listing.source
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(listing)
        
        # Display results by source
        for source, source_listings in by_source.items():
            print(f"\n{source}: {len(source_listings)} listings")
            print("-" * 60)
            for listing in source_listings:
                print(listing)
        
        # Summary
        print(f"\n{'='*60}")
        print(f"Summary by Source:")
        for source, source_listings in by_source.items():
            print(f"  {source}: {len(source_listings)} listings")
        print(f"{'='*60}\n")
