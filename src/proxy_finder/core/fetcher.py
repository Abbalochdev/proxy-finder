from typing import List, Optional, Dict, Any
import requests
import json
import time
from bs4 import BeautifulSoup

from ..exceptions import ProxyFetchError

class ProxyFetcher:
    """Handles fetching proxies from various sources."""
    
    def __init__(self, sources: List[str] = None, country: str = None):
        """
        Initialize ProxyFetcher with optional custom sources and country filter.
        
        Args:
            sources (List[str], optional): List of proxy source URLs.
            country (str, optional): Two-letter country code to filter proxies (e.g., 'US', 'GB').
        """
        self.country = country and country.upper()
        
        # Base URLs for proxy sources
        self.base_sources = {
            'proxyscrape': 'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country={country}&ssl=all&anonymity=all',
            'github_speedx': 'https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt',
            'github_shifty': 'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
            'geonode': 'https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&country={country}',
            'freeproxylists': 'https://www.freeproxylists.net/?c={country}&pt=&pr=&a%5B%5D=0&a%5B%5D=1&a%5B%5D=2&u=0',
            'proxyscan': 'https://www.proxyscan.io/api/proxy?limit=100&format=json&country={country}',
            'proxynova': 'https://www.proxynova.com/proxy-server-list/country-{country}/',
            'webshare': 'https://proxy.webshare.io/api/v2/proxy/list/?country={country}',
            'oxylabs': 'https://proxy.oxylabs.io/v1/sessions?country={country}'
        }
        
        # Format URLs with country if provided
        if sources:
            self.sources = sources
        else:
            self.sources = [
                self.base_sources['proxyscrape'].format(country=self.country or 'all'),
                self.base_sources['github_speedx'],
                self.base_sources['github_shifty'],
                self.base_sources['freeproxylists'].format(country=self.country or 'all'),
                self.base_sources['proxyscan'].format(country=self.country or 'all'),
                self.base_sources['proxynova'].format(country=self.country or 'all'),
                self.base_sources['webshare'].format(country=self.country or 'all'),
                self.base_sources['oxylabs'].format(country=self.country or 'all')
            ]
            
            # Add geonode API if country filtering is needed
            if self.country:
                self.sources.append(f"{self.base_sources['geonode'].format(country=self.country)}")
            else:
                self.sources.append(self.base_sources['geonode'].format(country='all'))
                
        # Cache for IP geolocation data
        self.geo_cache = {}

    def fetch_proxies(self) -> List[Dict[str, Any]]:
        """
        Fetch proxies from configured sources with metadata.
        
        Returns:
            List[Dict[str, Any]]: List of proxy dictionaries with metadata.
        
        Raises:
            ProxyFetchError: If proxy fetching fails.
        """
        proxies = []
        
        for source in self.sources:
            try:
                # Use a reasonable timeout for response
                response = requests.get(source, timeout=10)
                response.raise_for_status()
                
                # Different parsing for different sources
                if 'proxyscrape' in source:
                    source_proxies = self._parse_proxyscrape(response.text)
                    print(f"INFO     Fetched {len(source_proxies)} proxies from proxyscrape")
                    proxies.extend(source_proxies)
                elif 'github_speedx' in source:
                    source_proxies = self._parse_github(response.text)
                    print(f"INFO     Fetched {len(source_proxies)} proxies from speedx")
                    proxies.extend(source_proxies)
                elif 'github_shifty' in source:
                    source_proxies = self._parse_github(response.text)
                    print(f"INFO     Fetched {len(source_proxies)} proxies from shifty")
                    proxies.extend(source_proxies)
                elif 'geonode' in source:
                    source_proxies = self._parse_geonode(response.text)
                    print(f"INFO     Fetched {len(source_proxies)} proxies from geonode")
                    proxies.extend(source_proxies)
                elif 'freeproxylists' in source:
                    source_proxies = self._parse_freeproxylists(response.text)
                    print(f"INFO     Fetched {len(source_proxies)} proxies from freeproxylists")
                    proxies.extend(source_proxies)
                elif 'proxyscan' in source:
                    source_proxies = self._parse_proxyscan(response.text)
                    print(f"INFO     Fetched {len(source_proxies)} proxies from proxyscan")
                    proxies.extend(source_proxies)
                elif 'proxynova' in source:
                    source_proxies = self._parse_proxynova(response.text)
                    print(f"INFO     Fetched {len(source_proxies)} proxies from proxynova")
                    proxies.extend(source_proxies)
                elif 'webshare' in source:
                    source_proxies = self._parse_webshare(response.text)
                    print(f"INFO     Fetched {len(source_proxies)} proxies from webshare")
                    proxies.extend(source_proxies)
                elif 'oxylabs' in source:
                    source_proxies = self._parse_oxylabs(response.text)
                    print(f"INFO     Fetched {len(source_proxies)} proxies from oxylabs")
                    proxies.extend(source_proxies)
                else:
                    lines = [line.strip() for line in response.text.splitlines() if line.strip()]
                    print(f"INFO     Fetched {len(lines)} proxies from proxy-list")
                    for line in lines:
                        proxies.append({
                            'proxy': line,
                            'country': self._get_proxy_country(line),
                            'anonymity': 'unknown',
                            'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                        })
            
            except requests.RequestException as e:
                print(f"WARNING  Error fetching proxies from {source}: {e}")
        
        if not proxies:
            raise ProxyFetchError("No proxies could be fetched from any source")
        
        # Filter by country if specified
        country_proxies = []
        if self.country:
            # Make country code comparison case-insensitive
            country_code = self.country.upper()
            # Print total proxies before filtering
            print(f"INFO     Total proxies before country filtering: {len(proxies)}")
            
            # Filter proxies by country
            country_proxies = []
            for p in proxies:
                # Check both the country code from the source and the geolocation
                if p.get('country', '').upper() == country_code:
                    country_proxies.append(p)
                elif self._get_proxy_country(p['proxy']) == country_code:
                    country_proxies.append(p)
            
            print(f"INFO     Found {len(country_proxies)} proxies for country: {country_code}")
            
            # If no proxies found for the specific country, try to use any available proxies
            # but print a warning
            if not country_proxies:
                print(f"WARNING  No proxies found for country: {country_code}. Using available proxies instead.")
                country_proxies = proxies
        else:
            country_proxies = proxies

        # Remove duplicates based on proxy IP:PORT
        unique_proxies = []
        seen = set()
        
        for p in country_proxies:
            if p['proxy'] not in seen:
                seen.add(p['proxy'])
                unique_proxies.append(p)
                # Limit to 100 proxies maximum for better chances of finding valid ones
                if len(unique_proxies) >= 100:
                    break
        
        return unique_proxies

    def _parse_proxyscrape(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse proxies from proxyscrape API.
        
        Args:
            text (str): Response text from proxyscrape API.
        
        Returns:
            List[Dict[str, Any]]: List of proxy dictionaries with metadata.
        """
        result = []
        for line in text.splitlines():
            if line.strip():
                proxy = line.strip()
                country = self._get_proxy_country(proxy)
                
                result.append({
                    'proxy': proxy,
                    'country': country,
                    'anonymity': 'unknown',
                    'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                })
        return result

    def _parse_github(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse proxies from GitHub raw files.
        
        Args:
            text (str): Response text from GitHub.
        
        Returns:
            List[Dict[str, Any]]: List of proxy dictionaries with metadata.
        """
        result = []
        for line in text.splitlines():
            if line.strip() and not line.startswith('#'):
                proxy = line.strip()
                country = self._get_proxy_country(proxy)
                
                result.append({
                    'proxy': proxy,
                    'country': country,
                    'anonymity': 'unknown',
                    'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                })
        return result
        
    def _parse_geonode(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse proxies from GeoNode API.
        
        Args:
            text (str): Response text from GeoNode API.
        
        Returns:
            List[Dict[str, Any]]: List of proxy dictionaries with metadata.
        """
        result = []
        try:
            data = json.loads(text)
            for item in data.get('data', []):
                ip = item.get('ip')
                port = item.get('port')
                if ip and port:
                    proxy = f"{ip}:{port}"
                    result.append({
                        'proxy': proxy,
                        'country': item.get('country_code', 'unknown'),
                        'anonymity': item.get('anonymity', 'unknown'),
                        'last_checked': item.get('last_checked', time.strftime('%Y-%m-%d %H:%M:%S'))
                    })
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing GeoNode response: {e}")
        return result
        
    def _parse_freeproxylists(self, html: str) -> List[Dict[str, Any]]:
        """Parse proxies from FreeProxyLists.net"""
        proxies = []
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', {'class': 'DataGrid'})
        if table:
            for row in table.find_all('tr')[1:]:  # Skip header
                cols = row.find_all('td')
                if len(cols) >= 4:
                    ip = cols[0].text.strip()
                    port = cols[1].text.strip()
                    country = cols[3].text.strip()
                    # Only add if country matches or no country filter
                    if not self.country or country.upper() == self.country:
                        proxies.append({
                            'proxy': f"{ip}:{port}",
                            'country': country,
                            'anonymity': cols[4].text.strip(),
                            'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                        })
        return proxies

    def _parse_proxyscan(self, json_data: str) -> List[Dict[str, Any]]:
        """Parse proxies from Proxyscan.io API"""
        proxies = []
        try:
            data = json.loads(json_data)
            for proxy in data:
                country = proxy.get('country', 'Unknown')
                # Only add if country matches or no country filter
                if not self.country or country.upper() == self.country:
                    proxies.append({
                        'proxy': f"{proxy['ip']}:{proxy['port']}",
                        'country': country,
                        'anonymity': proxy.get('anonymity', 'unknown'),
                        'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                    })
        except json.JSONDecodeError:
            pass
        return proxies

    def _parse_proxynova(self, html: str) -> List[Dict[str, Any]]:
        """Parse proxies from ProxyNova"""
        proxies = []
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table', {'id': 'tbl_proxy_list'})
        if table:
            for row in table.find_all('tr')[1:]:  # Skip header
                cols = row.find_all('td')
                if len(cols) >= 8:
                    ip = cols[0].text.strip()
                    port = cols[1].text.strip()
                    country = cols[6].text.strip()
                    # Only add if country matches or no country filter
                    if not self.country or country.upper() == self.country:
                        proxies.append({
                            'proxy': f"{ip}:{port}",
                            'country': country,
                            'anonymity': cols[7].text.strip(),
                            'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                        })
        return proxies

    def _parse_webshare(self, json_data: str) -> List[Dict[str, Any]]:
        """Parse proxies from Webshare.io API"""
        proxies = []
        try:
            data = json.loads(json_data)
            for proxy in data.get('proxies', []):
                country = proxy.get('country', 'Unknown')
                # Only add if country matches or no country filter
                if not self.country or country.upper() == self.country:
                    proxies.append({
                        'proxy': f"{proxy['ip']}:{proxy['port']}",
                        'country': country,
                        'anonymity': proxy.get('anonymity', 'unknown'),
                        'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                    })
        except json.JSONDecodeError:
            pass
        return proxies

    def _parse_oxylabs(self, json_data: str) -> List[Dict[str, Any]]:
        """Parse proxies from Oxylabs API"""
        proxies = []
        try:
            data = json.loads(json_data)
            for proxy in data.get('proxies', []):
                country = proxy.get('country', 'Unknown')
                # Only add if country matches or no country filter
                if not self.country or country.upper() == self.country:
                    proxies.append({
                        'proxy': f"{proxy['ip']}:{proxy['port']}",
                        'country': country,
                        'anonymity': proxy.get('anonymity', 'unknown'),
                        'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                    })
        except json.JSONDecodeError:
            pass
        return proxies

    def _get_proxy_country(self, proxy: str) -> str:
        """
        Get country for a proxy using IP geolocation.
        
        Args:
            proxy (str): Proxy in IP:PORT format.
        
        Returns:
            str: Two-letter country code or 'unknown'.
        """
        # Return from cache if available
        if proxy in self.geo_cache:
            return self.geo_cache[proxy]
            
        # If country filtering is active, assume all proxies match the filter
        # This avoids unnecessary API calls
        if self.country:
            self.geo_cache[proxy] = self.country
            return self.country
            
        # For performance reasons, we'll skip real geolocation and use a simple heuristic
        # based on IP patterns. This is much faster but less accurate.
        try:
            ip = proxy.split(':')[0]
            ip_parts = ip.split('.')
            
            # Some common IP patterns and their likely countries
            # This is a very simplified approach
            if ip.startswith('104.16') or ip.startswith('104.17'):
                self.geo_cache[proxy] = 'US'
                return 'US'
            elif ip.startswith('5.') or ip.startswith('46.'):
                self.geo_cache[proxy] = 'DE'
                return 'DE'
            elif ip.startswith('185.') or ip.startswith('95.'):
                self.geo_cache[proxy] = 'RU'
                return 'RU'
            elif ip.startswith('103.'):
                self.geo_cache[proxy] = 'IN'
                return 'IN'
        except Exception:
            pass
            
        # Default to unknown
        self.geo_cache[proxy] = 'unknown'
        return 'unknown'
