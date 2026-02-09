# Path: searcher/markets/registry.py
"""
Market Registry

Central registry for market-specific searchers.
Maps market IDs to searcher implementations.
"""

from typing import Type

from searcher.constants import MARKET_SEC, MARKET_UK_FRC, MARKET_ESEF
from searcher.engine.base_searcher import BaseSearcher


# Market searcher registry
_SEARCHER_REGISTRY: dict[str, Type[BaseSearcher]] = {}


def register_searcher(market_id: str, searcher_class: Type[BaseSearcher]) -> None:
    """
    Register a searcher for a market.
    
    Args:
        market_id: Market identifier (e.g., 'sec', 'esma', 'fca')
        searcher_class: Searcher class implementing BaseSearcher
    """
    _SEARCHER_REGISTRY[market_id] = searcher_class


def get_searcher(market_id: str) -> BaseSearcher:
    """
    Get searcher instance for market.
    
    Args:
        market_id: Market identifier
        
    Returns:
        Searcher instance for market
        
    Raises:
        ValueError: If market not supported or not registered
    """
    if market_id not in _SEARCHER_REGISTRY:
        raise ValueError(
            f"Market '{market_id}' not registered. "
            f"Available markets: {list(_SEARCHER_REGISTRY.keys())}"
        )
    
    searcher_class = _SEARCHER_REGISTRY[market_id]
    return searcher_class()


def get_available_markets() -> list[str]:
    """
    Get list of registered markets.
    
    Returns:
        List of market IDs
    """
    return list(_SEARCHER_REGISTRY.keys())


# Auto-register SEC searcher if available
try:
    from searcher.markets.sec.searcher import SECSearcher
    register_searcher(MARKET_SEC, SECSearcher)
    print(f"INFO: SEC searcher registered (market: {MARKET_SEC})")
except ImportError as e:
    print(f"WARNING: Could not register SEC searcher: {e}")
    import traceback
    traceback.print_exc()

# Auto-register UK Companies House searcher
try:
    from searcher.markets.uk.searcher import UKSearcher
    register_searcher(MARKET_UK_FRC, UKSearcher)
    print(f"INFO: UK Companies House searcher registered (market: {MARKET_UK_FRC})")
except ImportError as e:
    print(f"WARNING: Could not register UK searcher: {e}")
    import traceback
    traceback.print_exc()

# Auto-register ESEF searcher (filings.xbrl.org)
try:
    from searcher.markets.esef.searcher import ESEFSearcher
    register_searcher(MARKET_ESEF, ESEFSearcher)
    print(f"INFO: ESEF searcher registered (market: {MARKET_ESEF})")
except ImportError as e:
    print(f"WARNING: Could not register ESEF searcher: {e}")
    import traceback
    traceback.print_exc()


__all__ = ['register_searcher', 'get_searcher', 'get_available_markets']