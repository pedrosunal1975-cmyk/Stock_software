# Path: searcher/markets/__init__.py
"""Markets Module - Market-Specific Search Implementations"""

from .registry import register_searcher, get_searcher, get_available_markets

__all__ = ['register_searcher', 'get_searcher', 'get_available_markets']