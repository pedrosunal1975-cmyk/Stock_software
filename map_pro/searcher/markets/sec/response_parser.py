# Path: searcher/markets/sec/response_parser.py
"""
SEC Response Parser

Handles content type detection for SEC API responses.
Critical for identifying when SEC returns HTML instead of JSON.
"""

import aiohttp


class ResponseContentType:
    """Content type enumeration."""
    JSON = 'json'
    HTML = 'html'
    UNKNOWN = 'unknown'


class SECResponseParser:
    """
    Parser for SEC API HTTP responses.
    
    Detects when SEC returns HTML (typically 404 pages) instead of JSON.
    This is normal for missing index.json files.
    """
    
    def detect_content_type(
        self,
        response: aiohttp.ClientResponse,
        response_text: str
    ) -> str:
        """
        Detect response content type.
        
        Args:
            response: aiohttp response object
            response_text: Response body text
            
        Returns:
            Content type (ResponseContentType enum value)
        """
        if self._is_html_response(response, response_text):
            return ResponseContentType.HTML
        
        if self._is_json_response(response_text):
            return ResponseContentType.JSON
        
        return ResponseContentType.UNKNOWN
    
    def _is_html_response(
        self,
        response: aiohttp.ClientResponse,
        response_text: str
    ) -> bool:
        """
        Check if response is HTML.
        
        Checks both Content-Type header and text content.
        
        Args:
            response: aiohttp response object
            response_text: Response body text
            
        Returns:
            True if response is HTML
        """
        # Check Content-Type header
        content_type = response.headers.get('Content-Type', '').lower()
        if 'text/html' in content_type:
            return True
        
        # Check text content
        text_start = response_text.strip()
        if text_start.startswith('<!DOCTYPE') or text_start.startswith('<html'):
            return True
        
        return False
    
    def _is_json_response(self, response_text: str) -> bool:
        """
        Check if response appears to be JSON.
        
        Args:
            response_text: Response body text
            
        Returns:
            True if response appears to be JSON
        """
        text_start = response_text.strip()
        return text_start.startswith('{') or text_start.startswith('[')


__all__ = ['SECResponseParser', 'ResponseContentType']