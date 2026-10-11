"""Data models for car listings."""

from dataclasses import dataclass
import hashlib
import re
from typing import Optional
from urllib.parse import urlsplit


@dataclass
class CarListing:
    """Represents a car listing from any source."""
    
    title: str
    price: Optional[str]
    year: Optional[str]
    make: str
    model: str
    mileage: Optional[str]
    location: Optional[str]
    url: str
    source: str
    description: Optional[str] = None
    external_id: Optional[str] = None

    def __post_init__(self):
        if not self.external_id and self.url:
            parsed = urlsplit(self.url)
            identifiers = re.findall(r'(?<!\d)\d{5,}(?!\d)', parsed.path)
            canonical_url = f'{parsed.netloc.lower()}{parsed.path.rstrip("/")}'
            self.external_id = identifiers[-1] if identifiers else hashlib.sha256(
                canonical_url.encode('utf-8')
            ).hexdigest()
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            'title': self.title,
            'price': self.price,
            'year': self.year,
            'make': self.make,
            'model': self.model,
            'mileage': self.mileage,
            'location': self.location,
            'url': self.url,
            'source': self.source,
            'description': self.description,
            'external_id': self.external_id
        }
    
    def __str__(self):
        """String representation of the car listing."""
        parts = [
            f"\n{'='*60}",
            f"Source: {self.source}",
            f"Title: {self.title}",
            f"Make: {self.make} | Model: {self.model}",
        ]
        
        if self.year:
            parts.append(f"Year: {self.year}")
        if self.price:
            parts.append(f"Price: {self.price}")
        if self.mileage:
            parts.append(f"Mileage: {self.mileage}")
        if self.location:
            parts.append(f"Location: {self.location}")
        
        parts.append(f"URL: {self.url}")
        
        if self.description:
            desc_preview = self.description[:150] + "..." if len(self.description) > 150 else self.description
            parts.append(f"Description: {desc_preview}")
        
        parts.append('='*60)
        
        return '\n'.join(parts)
