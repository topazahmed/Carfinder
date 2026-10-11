"""Environment-configured PostgreSQL connection and listing storage."""

import argparse
from contextlib import closing
import os

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import Json

from models import CarListing


def get_connection():
    load_dotenv()
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise RuntimeError('Set DATABASE_URL in your environment or .env file.')
    try:
        return psycopg2.connect(database_url, connect_timeout=10)
    except psycopg2.Error:
        raise RuntimeError('PostgreSQL connection failed. Check DATABASE_URL and database availability.') from None


class ListingStore:
    """Store listing snapshots with a source-scoped identity."""

    def initialize(self):
        with closing(get_connection()) as connection, connection, connection.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS car_listings (
                    source TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    payload JSONB NOT NULL,
                    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    PRIMARY KEY (source, external_id)
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS car_listings_vehicle_idx
                ON car_listings (lower(payload->>'make'), lower(payload->>'model'))
            ''')

    def save(self, listings):
        rows = {
            (listing.source, listing.external_id): listing
            for listing in listings if listing.external_id and listing.url
        }
        if not rows:
            return 0
        with closing(get_connection()) as connection, connection, connection.cursor() as cursor:
            cursor.executemany('''
                INSERT INTO car_listings (source, external_id, payload)
                VALUES (%s, %s, %s)
                ON CONFLICT (source, external_id) DO UPDATE
                SET payload = EXCLUDED.payload, last_seen = NOW()
            ''', [
                (listing.source, listing.external_id, Json(listing.to_dict()))
                for listing in rows.values()
            ])
        return len(rows)

    def search(self, make, model, location=None, limit=100):
        if not 1 <= limit <= 500:
            raise ValueError('limit must be between 1 and 500')
        with closing(get_connection()) as connection, connection, connection.cursor() as cursor:
            cursor.execute('''
                SELECT payload FROM car_listings
                WHERE lower(payload->>'make') = lower(%s)
                  AND lower(payload->>'model') = lower(%s)
                  AND (%s IS NULL OR strpos(lower(COALESCE(payload->>'location', '')), lower(%s)) > 0)
                ORDER BY last_seen DESC, source, external_id
                LIMIT %s
            ''', (make, model, location, location, limit))
            return [CarListing(**row[0]) for row in cursor.fetchall()]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Check PostgreSQL or initialize the listing schema')
    parser.add_argument('--init', action='store_true', help='Create the table and search index')
    args = parser.parse_args()
    if args.init:
        ListingStore().initialize()
        print('Listing schema initialized.')
    else:
        with closing(get_connection()) as connection, connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        print('PostgreSQL connection successful.')