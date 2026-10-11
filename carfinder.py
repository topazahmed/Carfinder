#!/usr/bin/env python3
"""
CarFinder - Multi-site Car Listing Aggregator

This tool searches for car listings across multiple websites including:
- Kijiji Autos
- AutoTrader
- Facebook Marketplace

Usage:
    python carfinder.py <make> <model> [--location LOCATION]

Examples:
    python carfinder.py Honda Civic
    python carfinder.py Toyota Camry --location Toronto
    python carfinder.py Ford F-150 --location "British Columbia"
"""

import argparse
import sys
import traceback
from aggregator import CarFinderAggregator


def main():
    """Main entry point for the CarFinder application."""
    parser = argparse.ArgumentParser(
        description='Search for car listings across multiple websites',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python carfinder.py Honda Civic
  python carfinder.py Toyota Camry --location Toronto
  python carfinder.py Ford F-150 --location "British Columbia"

Supported Sources:
  - Kijiji Autos
  - AutoTrader
  - Facebook Marketplace (limited support - requires JavaScript)
        """
    )
    
    parser.add_argument('make', help='Car make (e.g., Honda, Toyota, Ford)')
    parser.add_argument('model', help='Car model (e.g., Civic, Camry, F-150)')
    parser.add_argument(
        '--location', '-l',
        help='Location to search in (optional)',
        default=None
    )
    parser.add_argument(
        '--sequential', '-s',
        action='store_true',
        help='Run scrapers sequentially instead of in parallel (slower but easier to debug)'
    )
    parser.add_argument('--sources', nargs='+', choices=['autotrader', 'kijiji', 'facebook'],
                        help='Sources to search (default: all)')
    parser.add_argument('--require-database', action='store_true',
                        help='Require PostgreSQL persistence; suitable for scheduled jobs')
    
    args = parser.parse_args()
    
    # Create aggregator and run search
    aggregator = CarFinderAggregator(sources=args.sources)
    if args.require_database and not aggregator.store:
        parser.error('--require-database needs DATABASE_URL in the environment or .env')
    
    try:
        if aggregator.store:
            aggregator.store.initialize()
        aggregator.search_and_display(
            make=args.make,
            model=args.model,
            location=args.location,
            parallel=not args.sequential
        )
    except KeyboardInterrupt:
        print("\n\nSearch interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
