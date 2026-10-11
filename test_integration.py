"""Offline tests for browser rendering and persisted scrape workflows."""

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup
from autotrader_scraper import AutoTraderScraper
from kijiji_scraper import KijijiScraper
from conexion import ListingStore
from models import CarListing
from aggregator import CarFinderAggregator


def sample_listing(url='https://www.autotrader.ca/a/toyota/camry/5_123456/', price='$25,000'):
    return CarListing('2021 Toyota Camry', price, '2021', 'Toyota', 'Camry',
                      '40,000 km', 'Toronto', url, 'AutoTrader')


class StorageTests(unittest.TestCase):
    def test_identity_is_stable_across_tracking_urls(self):
        first = sample_listing()
        second = sample_listing(first.url + '?utm_source=email')
        self.assertEqual(first.external_id, '123456')
        self.assertEqual(first.external_id, second.external_id)

    def test_save_deduplicates_and_upserts_latest_price(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        with patch('conexion.get_connection', return_value=connection):
            saved = ListingStore().save([sample_listing(), sample_listing(price='$24,000')])
        self.assertEqual(saved, 1)
        query, rows = cursor.executemany.call_args.args
        self.assertIn('ON CONFLICT (source, external_id) DO UPDATE', query)
        self.assertEqual(rows[0][2].adapted['price'], '$24,000')
        connection.close.assert_called_once()

    def test_search_uses_parameters_and_restores_model(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [(sample_listing().to_dict(),)]
        with patch('conexion.get_connection', return_value=connection):
            result = ListingStore().search('Toyota', 'Camry', "Toronto' OR true --", 20)
        query, params = cursor.execute.call_args.args
        self.assertNotIn("Toronto' OR true --", query)
        self.assertEqual(params, ('Toyota', 'Camry', "Toronto' OR true --", "Toronto' OR true --", 20))
        self.assertEqual(result[0].external_id, '123456')


class WorkflowTests(unittest.TestCase):
    def test_all_sources_failing_is_not_an_empty_success(self):
        aggregator = CarFinderAggregator(sources=['autotrader'])
        scraper = aggregator.scrapers[0]
        scraper.last_error = 'HTTP 403'
        with patch.object(scraper, 'search', return_value=[]):
            with self.assertRaisesRegex(RuntimeError, 'All selected sources failed'):
                aggregator.search('Toyota', 'Camry', parallel=False)

    def test_partial_source_failure_keeps_successful_results(self):
        aggregator = CarFinderAggregator(sources=['autotrader', 'kijiji'])
        aggregator.store = None
        with patch.object(aggregator.scrapers[0], 'search', return_value=[sample_listing()]), patch.object(
            aggregator.scrapers[1], 'search', side_effect=RuntimeError('Unavailable')
        ):
            self.assertEqual(len(aggregator.search('Toyota', 'Camry', parallel=True)), 1)

    def test_aggregator_deduplicates_before_persisting(self):
        aggregator = CarFinderAggregator(sources=['autotrader'])
        aggregator.store = MagicMock()
        with patch.object(aggregator.scrapers[0], 'search', return_value=[sample_listing(), sample_listing()]):
            result = aggregator.search('Toyota', 'Camry', parallel=False)
        self.assertEqual(len(result), 1)
        aggregator.store.save.assert_called_once_with(result)

    def test_stored_api_returns_saved_results_without_scraping(self):
        import api
        with patch.object(api.aggregator, 'store') as store, patch.object(api.aggregator, 'search') as live:
            store.search.return_value = [sample_listing()]
            result = api.search_cars('Toyota', 'Camry', 'Toronto', True, 'stored', 20)
        self.assertEqual(result.total_count, 1)
        self.assertEqual(result.by_source, {'AutoTrader': 1})
        store.search.assert_called_once_with('Toyota', 'Camry', 'Toronto', 20)
        live.assert_not_called()

    def test_stored_api_requires_database(self):
        import api
        from fastapi import HTTPException
        with patch.object(api.aggregator, 'store', None):
            with self.assertRaises(HTTPException) as error:
                api.search_cars('Toyota', 'Camry', None, True, 'stored', 20)
        self.assertEqual(error.exception.status_code, 503)

    def test_cli_passes_sequential_and_initializes_database(self):
        import carfinder
        with patch('carfinder.CarFinderAggregator') as aggregator, patch.object(
            sys, 'argv', ['carfinder.py', 'Toyota', 'Camry', '--sequential', '--require-database', '--sources', 'autotrader']
        ):
            carfinder.main()
        aggregator.assert_called_once_with(sources=['autotrader'])
        aggregator.return_value.store.initialize.assert_called_once()
        aggregator.return_value.search_and_display.assert_called_once_with(
            make='Toyota', model='Camry', location=None, parallel=False
        )


class BrowserTests(unittest.TestCase):
    def test_current_kijiji_card_skips_image_link_and_extracts_fields(self):
        html = '''<section data-testid="listing-card" data-listingid="1741857475">
            <a href="/v-cars-trucks/toronto/camry/1741857475?imageNumber=1"><img alt="Camry"></a>
            <p data-testid="autos-listing-price">$23,242</p>
            <h3 data-testid="listing-title"><a data-testid="listing-link"
            href="/v-cars-trucks/toronto/camry/1741857475">2022 Toyota Camry SE</a></h3>
            <p>89530 km</p><p data-testid="listing-location">Toronto</p></section>'''
        listing = KijijiScraper()._parse_listing(BeautifulSoup(html, 'html.parser').section)
        self.assertEqual(listing.title, '2022 Toyota Camry SE')
        self.assertEqual(listing.price, '$23,242')
        self.assertEqual(listing.mileage, '89530 km')
        self.assertEqual(listing.location, 'Toronto')
        self.assertEqual(listing.external_id, '1741857475')
        self.assertNotIn('imageNumber', listing.url)

    def test_autotrader_parses_rendered_listing_selector(self):
        html = '''<div class="listing-item">
            <a class="result-title" href="/a/toyota/camry/5_123456/">2021 Toyota Camry</a>
            <span class="price-amount">$25,000</span><span class="kms">40,000 km</span>
            <span class="location">Toronto</span></div>'''
        scraper = AutoTraderScraper()
        with patch.object(scraper, 'fetch_page', return_value=BeautifulSoup(html, 'html.parser')) as fetch:
            listings = scraper.search('Toyota', 'Camry')
        self.assertEqual(len(listings), 1)
        self.assertEqual(listings[0].year, '2021')
        self.assertEqual(listings[0].price, '$25,000')
        fetch.assert_called_once_with('https://www.autotrader.ca/cars/toyota/camry/', '.result-item, .listing-item')

    def test_rendered_html_waits_for_selector_and_closes_browser(self):
        playwright = MagicMock()
        browser = playwright.chromium.launch.return_value
        page = browser.new_page.return_value
        page.goto.return_value.status = 200
        page.content.return_value = '<div class="result-item">Rendered listing</div>'
        context = MagicMock()
        context.__enter__.return_value = playwright
        module = SimpleNamespace(sync_playwright=lambda: context)
        with patch.dict(sys.modules, {'playwright.sync_api': module}), patch.dict(
            os.environ, {'SCRAPER_BACKEND': 'playwright'}, clear=True
        ):
            soup = AutoTraderScraper().fetch_page('https://example.com', '.result-item')
        self.assertEqual(soup.select_one('.result-item').text, 'Rendered listing')
        page.wait_for_selector.assert_called_once_with('.result-item', state='attached')
        browser.close.assert_called_once()

    def test_browser_closes_when_selector_times_out(self):
        playwright = MagicMock()
        browser = playwright.chromium.launch.return_value
        page = browser.new_page.return_value
        page.goto.return_value.status = 200
        page.wait_for_selector.side_effect = TimeoutError()
        context = MagicMock()
        context.__enter__.return_value = playwright
        with patch.dict(sys.modules, {'playwright.sync_api': SimpleNamespace(sync_playwright=lambda: context)}):
            self.assertIsNone(AutoTraderScraper()._fetch_rendered_page('https://example.com', '.listing'))
        browser.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()