#!/usr/bin/env python3
# Path: searcher/markets/seed_markets.py
"""
Seed Markets Table

Populates the database markets table with supported markets.
Uses constants from searcher.constants to avoid hardcoding.

Usage:
    python -m searcher.markets.seed_markets
"""

from database import initialize_database, session_scope
from database.models import Market
from searcher.constants import MARKETS_SEED_DATA


def seed_markets():
    """
    Populate markets table with supported markets.

    Reads market data from MARKETS_SEED_DATA constant.
    Idempotent - safe to run multiple times.
    """
    print("Seeding markets table...")

    with session_scope() as session:
        for market_data in MARKETS_SEED_DATA:
            # Check if market already exists
            existing = session.query(Market).filter_by(
                market_id=market_data['market_id']
            ).first()

            if existing:
                print(f"  ✓ Market '{market_data['market_id']}' already exists")
            else:
                market = Market(**market_data)
                session.add(market)
                print(f"  + Added market '{market_data['market_id']}': {market_data['market_name']}")

        session.commit()

    print("\n✓ Markets table seeded successfully!")


if __name__ == '__main__':
    # Initialize database first
    initialize_database()

    # Seed markets
    seed_markets()
