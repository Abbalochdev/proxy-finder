from typing import List, Dict, Any
import json
import time
import logging
import requests
from bs4 import BeautifulSoup
import re

from .base_fetcher import BaseProxyFetcher
from ..exceptions import ProxyFetchError

logger = logging.getLogger('proxy_finder')

class CountryProxyFetcher(BaseProxyFetcher):
    """Specialized proxy fetcher that focuses on country-specific proxies."""
    
    def __init__(self, country_code: str, timeout: float = 5.0):
        """Initialize country-specific proxy fetcher."""
        super().__init__(country_code, timeout)
        if not country_code:
            raise ValueError("Country code is required for CountryProxyFetcher")
            
        self.sources = self._build_sources()
        self.proxy_cache = {}  # Cache for validated proxies
        
    def _build_sources(self) -> List[Dict[str, Any]]:
        """Build country-specific proxy sources."""
        # List of reliable proxy sources with country filtering support
        sources = [
            {
                'name': 'GeoNode',
                'url': f'https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&filterUpTime=90&country={self.country}&protocols=http%2Chttps',
                'parser': self._parse_geonode,
                'headers': {
                    'Accept': 'application/json'
                }
            },
            {
                'name': 'FreeProxy',
                'url': f'https://www.freeproxy.world/?type=http&anonymity=&country={self.country}&speed=&port=&page=1',
                'parser': self._parse_freeproxy,
                'headers': {
                    'Referer': 'https://www.freeproxy.world/'
                }
            },
            {
                'name': 'ProxyScrape',
                'url': f'https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&country={self.country}&ssl=all&anonymity=all&timeout=5000',
                'parser': self._parse_text_list
            },
            {
                'name': 'OpenProxy',
                'url': f'https://openproxy.space/list/http/{self.country.lower()}',
                'parser': self._parse_openproxy,
                'headers': {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            },
            {
                'name': 'GatherProxy',
                'url': f'http://www.gatherproxy.com/proxylist/country/?c={self.country}',
                'parser': self._parse_gatherproxy
            }
        ]
        
        # Add backup sources that provide regular updates
        backup_sources = [
            {
                'name': 'TheSpeedX',
                'url': 'https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt',
                'parser': self._parse_text_list
            },
            {
                'name': 'Clarketm',
                'url': 'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt',
                'parser': self._parse_text_list
            },
            {
                'name': 'Monosans',
                'url': 'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt',
                'parser': self._parse_text_list
            }
        ]
        
        # Add backup sources only if fewer than 3 main sources are available
        if len(sources) < 3:
            sources.extend(backup_sources)
        
        return sources
        
    def fetch_proxies(self, max_proxies: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch and validate country-specific proxies.
        
        Args:
            max_proxies (int, optional): Maximum number of proxies to fetch. Defaults to 100.
            
        Returns:
            List[Dict[str, Any]]: List of validated proxies sorted by speed.
        """
        logger.info(f"Fetching country-specific proxies for {self.country}")
        
        # Store raw proxies per source to preserve them in case validation fails
        source_proxies = {}
        
        # Process each source individually to better track where proxies come from
        for source in self.sources:
            try:
                source_name = source['name']
                logger.info(f"Fetching from {source_name} for country {self.country}")
                
                response = requests.get(
                    source['url'], 
                    timeout=self.timeout,
                    headers=source.get('headers', {}),
                    verify=False
                )
                response.raise_for_status()
                
                # Skip empty responses
                if not response.text or response.text.isspace():
                    logger.warning(f"Empty response from {source_name}")
                    continue
                    
                # Parse proxies from this source
                proxies = source['parser'](response.text, source_name)
                source_proxies[source_name] = proxies
                logger.info(f"Fetched {len(proxies)} proxies from {source_name}")
                
            except Exception as e:
                logger.warning(f"Error fetching from {source_name}: {e}")
                continue
                
        # Combine all proxies
        all_proxies = []
        for source, proxies in source_proxies.items():
            all_proxies.extend(proxies)
        
        # If we didn't get enough proxies, also try the GitHub sources and filter by country
        if len(all_proxies) < max_proxies:
            logger.info("Adding GitHub-hosted proxy lists as fallback sources")
            github_sources = [
                {
                    'name': 'TheSpeedX',
                    'url': 'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
                    'parser': self._parse_text_list
                },
                {
                    'name': 'Clarketm',
                    'url': 'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt',
                    'parser': self._parse_text_list
                },
                {
                    'name': 'Monosans',
                    'url': 'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt',
                    'parser': self._parse_text_list
                }
            ]
            
            # Process GitHub sources
            for source in github_sources:
                try:
                    source_name = source['name']
                    response = requests.get(
                        source['url'], 
                        timeout=self.timeout,
                        verify=False
                    )
                    response.raise_for_status()
                    
                    # Skip empty responses
                    if not response.text or response.text.isspace():
                        continue
                        
                    # Parse proxies and manually filter for country
                    proxies = source['parser'](response.text, source_name)
                    country_proxies = []
                    
                    for proxy in proxies:
                        if proxy.get('country', 'unknown') == 'unknown':
                            # Try to determine country
                            detected_country = self._get_proxy_country(proxy['proxy'])
                            proxy['country'] = detected_country
                        
                        if proxy.get('country', '').upper() == self.country:
                            country_proxies.append(proxy)
                    
                    source_proxies[source_name] = country_proxies
                    all_proxies.extend(country_proxies)
                    logger.info(f"Found {len(country_proxies)} {self.country} proxies from {source_name}")
                    
                except Exception as e:
                    logger.warning(f"Error with GitHub source {source['name']}: {e}")
                    continue
        
        # Special handling for countries with very limited proxies
        limited_proxy_countries = ['SA', 'IR', 'KP', 'CU', 'SY', 'VE']
        
        if not all_proxies:
            # No proxies found from any source
            if self.country in limited_proxy_countries:
                logger.warning(f"No proxies found for {self.country}, which is a country with limited proxy availability")
            raise ProxyFetchError(f"No proxies found for country: {self.country}")
        
        # Look for FreeProxy sources first for limited countries like SA
        if self.country in limited_proxy_countries and 'FreeProxy' in source_proxies:
            free_proxies = source_proxies['FreeProxy']
            if free_proxies:
                logger.info(f"Using {len(free_proxies)} unvalidated proxies from FreeProxy for {self.country}")
                # Add speed values for sorting
                for proxy in free_proxies:
                    proxy['speed'] = 999.99
                    # Set validated flag
                    proxy['validated'] = False
                    proxy['last_checked'] = time.strftime('%Y-%m-%d %H:%M:%S')
                return free_proxies[:max_proxies]
            
        # Filter by country and deduplicate
        filtered_proxies = self._filter_and_deduplicate(all_proxies, max_proxies)
        
        # If filtered list is small, double check we're not filtering out valid proxies
        if len(filtered_proxies) < 5:
            logger.warning(f"Only found {len(filtered_proxies)} proxies for {self.country} after filtering")
            # Add some more detailed logging
            country_counts = {}
            for p in all_proxies:
                country = p.get('country', 'unknown').upper()
                country_counts[country] = country_counts.get(country, 0) + 1
            logger.info(f"Country distribution in all proxies: {country_counts}")
            
            # For countries with very few proxies, we'll keep all available proxies even if not validated
            if self.country in limited_proxy_countries and len(filtered_proxies) < 2:
                logger.info(f"Country {self.country} is known to have limited proxies, returning all found without strict validation")
                # Return all the found proxies for this country, even without validation
                country_filtered = [p for p in all_proxies if p.get('country', '').upper() == self.country]
                if country_filtered:
                    filtered_proxies = country_filtered
                    logger.info(f"Found {len(filtered_proxies)} raw proxies for {self.country}")
        
        # Validate the proxies
        validated_proxies = self._validate_proxies(filtered_proxies)
        
        if len(validated_proxies) == 0 and len(filtered_proxies) > 0:
            logger.warning(f"No proxies for {self.country} passed validation. Returning unvalidated proxies.")
            # Add speed estimates for sorting
            for proxy in filtered_proxies:
                if 'speed' not in proxy:
                    proxy['speed'] = 999.99  # High default speed for unvalidated proxies
                proxy['validated'] = False
                proxy['last_checked'] = time.strftime('%Y-%m-%d %H:%M:%S')
            return filtered_proxies[:max_proxies]
            
        # Sort by speed and limit to max_proxies
        return sorted(validated_proxies, key=lambda x: x.get('speed', float('inf')))[:max_proxies]
        
    def _validate_proxies(self, proxies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate proxies and measure their speed."""
        validated = []
        
        for proxy in proxies:
            # Skip if already validated recently
            if proxy['proxy'] in self.proxy_cache:
                cached = self.proxy_cache[proxy['proxy']]
                if time.time() - cached['timestamp'] < 3600:  # Cache for 1 hour
                    validated.append(cached)
                    continue
                    
            try:
                # Quick check
                start_time = time.time()
                response = requests.get(
                    'http://example.com',
                    proxies={'http': f"http://{proxy['proxy']}", 'https': f"http://{proxy['proxy']}"},
                    timeout=self.timeout,
                    verify=False,
                    allow_redirects=False
                )
                response.raise_for_status()
                
                # Calculate speed
                speed = time.time() - start_time
                
                validated_proxy = {
                    **proxy,
                    'validated': True,
                    'speed': speed,
                    'last_checked': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'timestamp': time.time()
                }
                
                self.proxy_cache[proxy['proxy']] = validated_proxy
                validated.append(validated_proxy)
                
            except Exception as e:
                if not isinstance(e, requests.exceptions.Timeout):
                    logger.debug(f"Validation failed for {proxy['proxy']}: {e}")
                continue
                
        return validated
    
    def _parse_geonode(self, text: str, source_name: str) -> List[Dict[str, Any]]:
        """
        Parse proxies from GeoNode API.
        
        Args:
            text (str): Response text from GeoNode API
            source_name (str): Name of the source for logging
            
        Returns:
            List[Dict[str, Any]]: List of parsed proxies
        """
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
    
    def _parse_proxyscan(self, text: str, source_name: str) -> List[Dict[str, Any]]:
        """
        Parse proxies from ProxyScan API.
        
        Args:
            text (str): Response text
            source_name (str): Name of the source for logging
            
        Returns:
            List[Dict[str, Any]]: List of parsed proxies
        """
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
        except Exception as e:
            logger.warning(f"Error parsing ProxyScan response: {e}")
        return result
    
    def _parse_text_list(self, text: str, source_name: str) -> List[Dict[str, Any]]:
        """Parse proxies from text list."""
        result = []
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                # Validate proxy format
                if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}$', line):
                    result.append({
                        'proxy': line,
                        'country': self.country,  # We know the country since this is country-specific fetcher
                        'anonymity': 'unknown',
                        'source': source_name,
                        'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                    })
        return result
    
    def _parse_proxynova(self, text: str, source_name: str) -> List[Dict[str, Any]]:
        """Parse proxies from ProxyNova."""
        result = []
        try:
            soup = BeautifulSoup(text, 'html.parser')
            table = soup.find('table', {'id': 'tbl_proxy_list'})
            if table:
                for row in table.find_all('tr')[1:]:  # Skip header
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        ip = cols[0].text.strip()
                        port = cols[1].text.strip()
                        if ip and port and re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
                            result.append({
                                'proxy': f"{ip}:{port}",
                                'country': self.country,
                                'anonymity': cols[6].text.strip() if len(cols) > 6 else 'unknown',
                                'source': source_name,
                                'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                            })
        except Exception as e:
            logger.warning(f"Error parsing ProxyNova response: {e}")
        return result
    
    def _parse_hidemyname(self, text: str, source_name: str) -> List[Dict[str, Any]]:
        """Parse proxies from HideMyName."""
        result = []
        try:
            soup = BeautifulSoup(text, 'html.parser')
            table = soup.find('table', {'class': 'proxy__t'})
            if table:
                for row in table.find_all('tr')[1:]:  # Skip header
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        ip = cols[0].text.strip()
                        port = cols[1].text.strip()
                        if ip and port and re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
                            result.append({
                                'proxy': f"{ip}:{port}",
                                'country': self.country,
                                'anonymity': cols[5].text.strip() if len(cols) > 5 else 'unknown',
                                'source': source_name,
                                'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                            })
        except Exception as e:
            logger.warning(f"Error parsing HideMyName response: {e}")
        return result
    
    def _parse_freeproxy(self, text: str, source_name: str) -> List[Dict[str, Any]]:
        """Parse proxies from FreeProxy World."""
        result = []
        try:
            soup = BeautifulSoup(text, 'html.parser')
            table = soup.find('table', {'class': 'layui-table'})
            if table:
                for row in table.find_all('tr')[1:]:  # Skip header
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        ip = cols[0].text.strip()
                        port = cols[1].text.strip()
                        if ip and port and re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
                            result.append({
                                'proxy': f"{ip}:{port}",
                                'country': self.country,
                                'anonymity': cols[3].text.strip() if len(cols) > 3 else 'unknown',
                                'source': source_name,
                                'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                            })
        except Exception as e:
            logger.warning(f"Error parsing FreeProxy response: {e}")
        return result
    
    def _parse_openproxy(self, text: str, source_name: str) -> List[Dict[str, Any]]:
        """Parse proxies from OpenProxy Space."""
        result = []
        try:
            data = json.loads(text)
            for item in data.get('list', []):
                ip = item.get('ip')
                port = item.get('port')
                if ip and port:
                    result.append({
                        'proxy': f"{ip}:{port}",
                        'country': self.country,
                        'anonymity': item.get('anonymity', 'unknown'),
                        'source': source_name,
                        'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                    })
        except Exception as e:
            logger.warning(f"Error parsing OpenProxy response: {e}")
        return result
    
    def _parse_gatherproxy(self, text: str, source_name: str) -> List[Dict[str, Any]]:
        """Parse proxies from GatherProxy."""
        result = []
        try:
            soup = BeautifulSoup(text, 'html.parser')
            script_content = soup.find_all('script', text=re.compile(r'gp.insertPrx'))
            
            for script in script_content:
                match = re.search(r'"PROXY_IP":"([^"]+)".*?"PROXY_PORT":"([^"]+)"', script.string)
                if match:
                    ip, port = match.groups()
                    # Port is usually in hex format
                    try:
                        port = str(int(port, 16))
                    except ValueError:
                        continue
                        
                    result.append({
                        'proxy': f"{ip}:{port}",
                        'country': self.country,
                        'anonymity': 'unknown',
                        'source': source_name,
                        'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                    })
        except Exception as e:
            logger.warning(f"Error parsing GatherProxy response: {e}")
        return result
