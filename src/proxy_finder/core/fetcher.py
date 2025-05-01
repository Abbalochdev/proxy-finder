from typing import List, Dict, Any
import json
import time
import logging
from bs4 import BeautifulSoup

from .base_fetcher import BaseProxyFetcher
from ..exceptions import ProxyFetchError

logger = logging.getLogger('proxy_finder')

class BasicProxyFetcher(BaseProxyFetcher):
    """Basic proxy fetcher with essential functionality."""
    
    def __init__(self, country: str = None, timeout: float = 5.0):
        """Initialize basic proxy fetcher."""
        super().__init__(country, timeout)
        self.sources = self._build_sources()
        
    def _build_sources(self) -> List[Dict[str, Any]]:
        """Build basic proxy sources."""
        sources = [
            {
                'name': 'proxyscrape',
                'url': f'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country={self.country or "all"}&ssl=all&anonymity=all',
                'parser': self._parse_text_list
            },
            {
                'name': 'github-speedx',
                'url': 'https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt',
                'parser': self._parse_text_list
            },
            {
                'name': 'github-shifty',
                'url': 'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
                'parser': self._parse_text_list
            }
        ]
        
        # Add geonode API if country filtering is needed
        if self.country:
            sources.append({
                'name': 'geonode',
                'url': f'https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&country={self.country}',
                'parser': self._parse_geonode
            })
        
        return sources
        
    def fetch_proxies(self, max_proxies: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch proxies from basic sources.
        
        Args:
            max_proxies (int, optional): Maximum number of proxies to fetch. Defaults to 100.
            
        Returns:
            List[Dict[str, Any]]: List of proxy dictionaries with metadata.
        """
        all_proxies = self._fetch_with_concurrent(self.sources)
        
        if not all_proxies:
            raise ProxyFetchError("No proxies could be fetched from any source")
            
        return self._filter_and_deduplicate(all_proxies, max_proxies)
        
    def _parse_geonode(self, text: str, source_name: str) -> List[Dict[str, Any]]:
        """Parse proxies from GeoNode API."""
        result = []
        try:
            data = json.loads(text)
            for item in data.get('data', []):
                ip = item.get('ip')
                port = item.get('port')
                if ip and port:
                    proxy = f"{ip}:{port}"
                    country_code = item.get('country_code', 'unknown')
                    
                    # Skip if country filter is active and doesn't match
                    if self.country and country_code != self.country:
                        continue
                        
                    result.append({
                        'proxy': proxy,
                        'country': country_code,
                        'anonymity': item.get('anonymity', 'unknown'),
                        'source': source_name,
                        'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                    })
        except Exception as e:
            logger.warning(f"Error parsing GeoNode response: {e}")
        return result
