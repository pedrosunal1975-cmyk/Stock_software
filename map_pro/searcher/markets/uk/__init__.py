# Path: searcher/markets/uk/__init__.py
"""
UK Companies House Market Searcher

Implements searching and downloading of XBRL filings from Companies House.

Key Components:
- UKSearcher: Main searcher class
- UKAPIClient: Companies House API client
- Company number resolution and validation
- iXBRL document downloading
"""

from .searcher import UKSearcher
from .constants import MARKET_ID

__all__ = [
    'UKSearcher',
    'MARKET_ID',
]
