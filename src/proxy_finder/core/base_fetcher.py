from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
import requests
import json
import time
import re
from bs4 import BeautifulSoup
import logging
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..exceptions import ProxyFetchError

# Configure urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Setup logging
logger = logging.getLogger('proxy_finder')

class BaseProxyFetcher(ABC):
    """Abstract base class for proxy fetchers with common functionality."""
    
    def __init__(self, country: str = None, timeout: float = 5.0, max_sources: int = 5):
        """
        Initialize base proxy fetcher.
        
        Args:
            country (str, optional): Two-letter country code to filter proxies.
            timeout (float): Request timeout in seconds.
            max_sources (int): Maximum number of sources to query.
        """
        self.country = country and country.upper()
        self.timeout = timeout
        self.max_sources = max_sources
        self.geo_cache = {}  # Cache for IP geolocation
        
    @abstractmethod
    def fetch_proxies(self, max_proxies: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch proxies from configured sources.
        
        Args:
            max_proxies (int, optional): Maximum number of proxies to fetch. Defaults to 100.
            
        Returns:
            List[Dict[str, Any]]: List of proxy dictionaries with metadata.
            
        Raises:
            ProxyFetchError: If proxy fetching fails.
        """
        pass
        
    def _fetch_with_concurrent(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fetch proxies from multiple sources concurrently.
        
        Args:
            sources (List[Dict[str, Any]]): List of source configurations.
            
        Returns:
            List[Dict[str, Any]]: Combined list of proxies.
        """
        all_proxies = []
        
        with ThreadPoolExecutor(max_workers=min(len(sources), 5)) as executor:
            future_to_source = {
                executor.submit(self._fetch_from_source, source): source
                for source in sources
            }
            
            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    proxies = future.result()
                    all_proxies.extend(proxies)
                    logger.info(f"Fetched {len(proxies)} proxies from {source['name']}")
                except Exception as e:                    logger.warning(f"Error fetching from {source['name']}: {e}")
                    
        return all_proxies
        
    def _fetch_from_source(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch proxies from a single source.
        
        Args:
            source (Dict[str, Any]): Source configuration.
            
        Returns:
            List[Dict[str, Any]]: List of proxies from this source.
        """
        try:
            # Default headers that work with most services
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Update with source-specific headers if provided
            if 'headers' in source:
                headers.update(source['headers'])
            
            response = requests.get(
                source['url'], 
                timeout=self.timeout,
                headers=headers,
                verify=False  # Some proxy sites use self-signed certificates
            )
            response.raise_for_status()
            
            # Check if response is empty or invalid
            if not response.text or response.text.isspace():
                logger.warning(f"Empty response from {source['name']}")
                return []
                
            return source['parser'](response.text, source['name'])
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Error fetching from {source['name']}: {e}")
            return []
        except Exception as e:
            logger.warning(f"Unexpected error from {source['name']}: {e}")
            return []
            
    def _filter_and_deduplicate(self, proxies: List[Dict[str, Any]], 
                              max_proxies: int = 100) -> List[Dict[str, Any]]:
        """
        Filter and deduplicate proxies.
        
        Args:
            proxies (List[Dict[str, Any]]): List of proxy dictionaries.
            max_proxies (int): Maximum number of proxies to return.
            
        Returns:
            List[Dict[str, Any]]: Filtered and deduplicated proxy list.
        """
        unique_proxies = []
        seen = set()
        country_count = 0
        
        for proxy_data in proxies:
            proxy_str = proxy_data.get('proxy', '')
            if not proxy_str:
                continue
            
            # Basic format validation
            if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}$', proxy_str):
                continue
            
            # Deduplicate
            if proxy_str not in seen:
                seen.add(proxy_str)
            
            # Apply country filter if specified
            if self.country:
                proxy_country = proxy_data.get('country', 'unknown').upper()
                target_country = self.country.upper()
                
                if proxy_country != target_country:
                    # As a backup, try to detect the country using pattern matching
                    if proxy_country == 'UNKNOWN':
                        detected_country = self._get_proxy_country(proxy_str)
                        proxy_data['country'] = detected_country
                        if detected_country.upper() == target_country:
                            unique_proxies.append(proxy_data)
                            country_count += 1
                    continue
                else:
                    country_count += 1
            
            unique_proxies.append(proxy_data)
            
            # Limit to max_proxies
            if len(unique_proxies) >= max_proxies:
                break
                
        if self.country:
            logger.info(f"Found {country_count} proxies for country {self.country} out of {len(seen)} unique proxies")
        
        return unique_proxies
    
    def _get_proxy_country(self, proxy: str) -> str:
        """
        Get country for a proxy using IP pattern matching.
        
        Args:
            proxy (str): Proxy in IP:PORT format.
            
        Returns:
            str: Two-letter country code or 'unknown'.
        """
        if proxy in self.geo_cache:
            return self.geo_cache[proxy]
            
        try:
            ip = proxy.split(':')[0]
            
            # Common IP patterns for countries
            country_patterns = {
                # United States
                r'^(104\.16|104\.17|144\.|146\.|147\.|148\.|149\.|152\.|153\.|154\.|155\.|156\.|'
                r'165\.|166\.|167\.|168\.|169\.|170\.|171\.|172\.|173\.|174\.|192\.|198\.|199\.|'
                r'204\.|205\.|206\.|207\.|208\.|209\.|216\.|63\.|64\.|65\.|66\.|67\.|68\.|69\.|'
                r'70\.|71\.|72\.|73\.|74\.|75\.|76\.|96\.|97\.|98\.|99\.)': 'US',
                
                # Germany
                r'^(5\.|46\.)': 'DE',
                
                # Russia
                r'^(185\.|95\.)': 'RU',
                
                # India
                r'^103\.': 'IN',
                
                # China
                r'^(1\.|116\.|118\.|121\.|122\.|123\.|124\.|125\.|222\.|223\.|58\.|59\.|60\.|61\.)': 'CN',
                
                # South Korea
                r'^(14\.|111\.|112\.|211\.)': 'KR',
                
                # Singapore
                r'^(119\.|175\.|202\.)': 'SG',
                
                # France
                r'^195\.': 'FR',
                
                # Netherlands
                r'^91\.': 'NL',
                
                # Mexico
                r'^(200\.|201\.)': 'MX',
                
                # Brazil
                r'^(45\.|187\.|189\.)': 'BR',
                
                # United Kingdom
                r'^213\.': 'GB',
                
                # Japan
                r'^139\.': 'JP',
                
                # Australia
                r'^203\.': 'AU'
            }
            
            for pattern, country in country_patterns.items():
                if re.match(pattern, ip):
                    self.geo_cache[proxy] = country
                    return country
                    
        except Exception:
            pass
            
        # Default to unknown
        self.geo_cache[proxy] = 'unknown'
        return 'unknown'
    
    @staticmethod
    def _parse_text_list(text: str, source_name: str) -> List[Dict[str, Any]]:
        """
        Parse a text list of proxies (one per line).
        
        Args:
            text (str): Text content with one proxy per line.
            source_name (str): Name of the source for logging.
            
        Returns:
            List[Dict[str, Any]]: List of proxy dictionaries.
        """
        result = []
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                # Validate proxy format
                if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}$', line):
                    result.append({
                        'proxy': line,
                        'country': 'unknown',  # Will be updated by the fetcher
                        'anonymity': 'unknown',
                        'source': source_name,
                        'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                    })
        return result