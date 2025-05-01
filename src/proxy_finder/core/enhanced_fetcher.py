from typing import List, Dict, Any
import json
import time
import logging
from bs4 import BeautifulSoup

from .base_fetcher import BaseProxyFetcher
from ..exceptions import ProxyFetchError

logger = logging.getLogger('proxy_finder')

class ProxyFetcher(BaseProxyFetcher):
    """Enhanced proxy fetcher with advanced source management and filtering."""

    def __init__(self, country: str = None, timeout: float = 10.0, max_sources: int = 8):
        """Initialize enhanced proxy fetcher."""
        super().__init__(country, timeout, max_sources)
        self.country_map = self._build_country_map()
        self.sources = self._build_sources()

    def _build_country_map(self) -> Dict[str, str]:
        """Build a mapping of country names to ISO country codes."""
        return {
            'united states': 'US', 'usa': 'US', 'united kingdom': 'GB', 'uk': 'GB',
            'germany': 'DE', 'france': 'FR', 'canada': 'CA', 'australia': 'AU',
            'netherlands': 'NL', 'russia': 'RU', 'china': 'CN', 'japan': 'JP',
            'brazil': 'BR', 'india': 'IN', 'singapore': 'SG', 'south korea': 'KR',
            'italy': 'IT', 'spain': 'ES', 'sweden': 'SE', 'switzerland': 'CH',
            'poland': 'PL', 'turkey': 'TR', 'mexico': 'MX', 'indonesia': 'ID',
            'thailand': 'TH', 'vietnam': 'VN', 'ukraine': 'UA', 'egypt': 'EG',
            'south africa': 'ZA', 'argentina': 'AR', 'pakistan': 'PK', 'malaysia': 'MY',
            'ireland': 'IE', 'denmark': 'DK', 'finland': 'FI', 'norway': 'NO',
            'belgium': 'BE', 'austria': 'AT', 'portugal': 'PT', 'greece': 'GR'
        }

    def _build_sources(self) -> List[Dict[str, Any]]:
        """Build a list of proxy sources with metadata."""
        # Updated list of sources with current working APIs as of 2024
        sources = [
            # GitHub-hosted public proxy lists (more reliable than API endpoints)
            {
                'name': 'github-clarketm',
                'url': 'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt',
                'parser': self._parse_text_list,
                'priority': 1,
                'supports_country': False
            },
            {
                'name': 'github-speedx',
                'url': 'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
                'parser': self._parse_text_list,
                'priority': 1,
                'supports_country': False
            },
            {
                'name': 'github-monosans',
                'url': 'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt',
                'parser': self._parse_text_list,
                'priority': 1,
                'supports_country': False
            },
            {
                'name': 'proxyscrape',
                'url': f'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country={self.country or "all"}&ssl=all&anonymity=all',
                'parser': self._parse_text_list,
                'priority': 2,
                'supports_country': True
            },
            {
                'name': 'geonode',
                'url': f'https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc{f"&country={self.country}" if self.country else ""}',
                'parser': self._parse_geonode,
                'priority': 2,
                'supports_country': True
            },
            # Fallback to free-proxy-list.net (HTML scraping)
            {
                'name': 'free-proxy-list', 
                'url': 'https://free-proxy-list.net/',
                'parser': self._parse_free_proxy_list,
                'priority': 3,
                'supports_country': False
            }
        ]

        # Filter sources based on country support if country is specified
        if self.country:
            # Prioritize sources that support country filtering
            sources.sort(key=lambda s: 0 if s['supports_country'] else 1)

        # Sort by priority and limit to max_sources
        sources.sort(key=lambda s: s['priority'])
        return sources[:self.max_sources]

    def get_available_countries(self) -> Dict[str, str]:
        """Get list of available countries for proxies."""
        return self.country_map

    def fetch_proxies(self, max_proxies: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch proxies from multiple sources concurrently.

        Args:
            max_proxies (int, optional): Maximum number of proxies to fetch. Defaults to 100.

        Returns:
            List[Dict[str, Any]]: List of proxy dictionaries with metadata.

        Raises:
            ProxyFetchError: If no proxies could be fetched from any source.
        """
        logger.info(f"Fetching proxies from {len(self.sources)} sources")
        all_proxies = self._fetch_with_concurrent(self.sources)
        
        if all_proxies:
            logger.info(f"Found {len(all_proxies)} proxies before filtering")
        else:
            logger.warning("No proxies found from any source")

        # For proxies with unknown country, try to determine their country
        if self.country:
            logger.info(f"Filtering for country: {self.country}")
            for proxy in all_proxies:
                if proxy.get('country', 'unknown') == 'unknown':
                    # Try to determine country
                    ip = proxy['proxy'].split(':')[0]
                    proxy['country'] = self._get_proxy_country(proxy['proxy'])
                    
        # Filter and deduplicate
        filtered_proxies = self._filter_and_deduplicate(all_proxies, max_proxies)
        logger.info(f"Returning {len(filtered_proxies)} unique proxies after filtering")
        
        if not filtered_proxies:
            raise ProxyFetchError("No proxies could be fetched from any source")
            
        return filtered_proxies

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
                        'last_checked': item.get('last_checked', time.strftime('%Y-%m-%d %H:%M:%S'))
                    })
            logger.info(f"Parsed {len(result)} proxies from GeoNode API")
        except Exception as e:
            logger.warning(f"Error parsing GeoNode response: {e}")
        return result

    def _parse_proxyscan(self, text: str, source_name: str) -> List[Dict[str, Any]]:
        """Parse proxies from ProxyScan API."""
        result = []
        try:
            data = json.loads(text)
            for item in data:
                ip = item.get('Ip')
                port = item.get('Port')
                if ip and port:
                    proxy = f"{ip}:{port}"
                    country_code = item.get('Country', {}).get('Iso', 'unknown')

                    # Skip if country filter is active and doesn't match
                    if self.country and country_code != self.country:
                        continue

                    result.append({
                        'proxy': proxy,
                        'country': country_code,
                        'anonymity': item.get('Type', ['unknown'])[0].lower() if item.get('Type') else 'unknown',
                        'source': source_name,
                        'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                    })
            logger.info(f"Parsed {len(result)} proxies from ProxyScan API")
        except Exception as e:
            logger.warning(f"Error parsing ProxyScan response: {e}")
        return result
        
    def _parse_free_proxy_list(self, text: str, source_name: str) -> List[Dict[str, Any]]:
        """Parse proxies from free-proxy-list.net HTML."""
        result = []
        try:
            soup = BeautifulSoup(text, 'html.parser')
            table = soup.find('table')
            
            if not table:
                return []
                
            # Process table rows
            for row in table.find_all('tr')[1:]:  # Skip header row
                cells = row.find_all('td')
                if len(cells) >= 8:
                    ip = cells[0].text.strip()
                    port = cells[1].text.strip()
                    country_code = cells[2].text.strip()
                    anonymity = cells[4].text.strip().lower()
                    
                    if ip and port:
                        proxy = f"{ip}:{port}"
                        
                        # Skip if country filter is active and doesn't match
                        if self.country and country_code != self.country:
                            continue
                            
                        result.append({
                            'proxy': proxy,
                            'country': country_code,
                            'anonymity': anonymity,
                            'source': source_name,
                            'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                        })
            logger.info(f"Parsed {len(result)} proxies from free-proxy-list.net")
        except Exception as e:
            logger.warning(f"Error parsing free-proxy-list.net HTML: {e}")
        return result
