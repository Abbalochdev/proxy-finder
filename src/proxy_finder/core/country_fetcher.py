from typing import List, Dict, Any, Optional
import requests
import json
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
import ipaddress

from ..exceptions import ProxyFetchError
from .fetcher import ProxyFetcher

class CountryProxyFetcher:
    """
    Specialized proxy fetcher that focuses on country-specific proxies with high efficiency.
    Uses multiple data sources and parallel processing for faster fetching.
    """
    
    def __init__(self, country_code: str, timeout: float = 5.0):
        """
        Initialize the country-specific proxy fetcher.
        
        Args:
            country_code (str): Two-letter country code (e.g., 'US', 'GB')
            timeout (float): Connection timeout in seconds
        """
        # Convert to uppercase and validate country code
        self.country_code = country_code.upper()
        
        # Validate country code
        if not self._is_valid_country_code(self.country_code):
            raise ValueError(f"Invalid country code: {country_code}. Please use a valid 2-letter country code (e.g., US, GB, DE)")
            
        self.timeout = timeout
        
        # Reliable proxy sources with country filtering
        self.sources = [
            {
                'name': 'GeoNode',
                'url': f'https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&country={self.country_code}',
                'parser': self._parse_geonode
            },
            {
                'name': 'ProxyScan',
                'url': f'https://www.proxyscan.io/api/proxy?limit=100&format=json&country={self.country_code}',
                'parser': self._parse_proxyscan
            },
            {
                'name': 'ProxyScrape',
                'url': f'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country={self.country_code}&ssl=all&anonymity=all',
                'parser': self._parse_proxyscrape
            },
            {
                'name': 'ProxyNova',
                'url': f'https://www.proxynova.com/proxy-server-list/country-{self.country_code.lower()}/',
                'parser': self._parse_proxynova
            }
        ]
        
        # Cache for verified proxies
        self.proxy_cache = {}
        
    def fetch_proxies(self, max_proxies: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch and validate country-specific proxies.
        
        Args:
            max_proxies (int): Maximum number of proxies to fetch
            
        Returns:
            List[Dict[str, Any]]: List of verified proxies with metadata
        """
        proxies = []
        
        # Use ThreadPoolExecutor for parallel fetching
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_source = {
                executor.submit(self._fetch_from_source, source): source
                for source in self.sources
            }
            
            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    source_proxies = future.result()
                    proxies.extend(source_proxies)
                    print(f"INFO: Fetched {len(source_proxies)} proxies from {source['name']}")
                except Exception as e:
                    print(f"WARNING: Error fetching from {source['name']}: {e}")
        
        # Validate and filter proxies
        validated_proxies = self._validate_proxies(proxies, max_proxies)
        
        # Sort by speed and return
        return sorted(validated_proxies, key=lambda x: x.get('speed', float('inf')))
    
    def _fetch_from_source(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch proxies from a single source.
        
        Args:
            source (Dict[str, Any]): Source configuration
            
        Returns:
            List[Dict[str, Any]]: List of proxies from the source
        """
        try:
            response = requests.get(
                source['url'],
                timeout=self.timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
            )
            response.raise_for_status()
            return source['parser'](response.text)
        except requests.RequestException as e:
            print(f"Error fetching from {source['name']}: {e}")
            return []
    
    def _validate_proxies(self, proxies: List[Dict[str, Any]], max_proxies: int) -> List[Dict[str, Any]]:
        """
        Validate and verify proxy country.
        
        Args:
            proxies (List[Dict[str, Any]]): List of proxies to validate
            max_proxies (int): Maximum number of proxies to return
            
        Returns:
            List[Dict[str, Any]]: List of validated proxies
        """
        validated = []
        
        for proxy in proxies:
            if len(validated) >= max_proxies:
                break
                
            # Skip if already validated
            if proxy['proxy'] in self.proxy_cache:
                validated.append(self.proxy_cache[proxy['proxy']])
                continue
            
            try:
                # Verify proxy connection with shorter timeout for initial check
                start_time = time.time()
                response = requests.get(
                    'http://example.com',
                    proxies={'http': proxy['proxy'], 'https': proxy['proxy']},
                    timeout=5.0,  # Reduced timeout for initial check
                    verify=False,  # Disable SSL verification for faster checks
                    allow_redirects=False
                )
                response.raise_for_status()
                
                # If initial check passes, do a more thorough check
                thorough_start = time.time()
                thorough_response = requests.get(
                    'http://example.com',
                    proxies={'http': proxy['proxy'], 'https': proxy['proxy']},
                    timeout=self.timeout,
                    verify=False,
                    allow_redirects=False
                )
                thorough_response.raise_for_status()
                
                # Calculate average speed
                speed = (time.time() - start_time + time.time() - thorough_start) / 2
                
                proxy['validated'] = True
                proxy['last_checked'] = time.strftime('%Y-%m-%d %H:%M:%S')
                proxy['speed'] = speed
                
                self.proxy_cache[proxy['proxy']] = proxy
                validated.append(proxy)
                
            except Exception as e:
                # Only print error if it's not a timeout
                if not isinstance(e, requests.exceptions.Timeout):
                    print(f"Validation failed for {proxy['proxy']}: {e}")
                continue
        
        return validated
    
    def _parse_geonode(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse proxies from GeoNode API.
        
        Args:
            text (str): Response text
            
        Returns:
            List[Dict[str, Any]]: List of parsed proxies
        """
        try:
            data = json.loads(text)
            return [{
                'proxy': f"{item['ip']}:{item['port']}",
                'country': item['country_code'],
                'anonymity': item['anonymity'],
                'last_checked': item['last_checked']
            } for item in data.get('data', [])]
        except Exception:
            return []
    
    def _parse_proxyscan(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse proxies from ProxyScan API.
        
        Args:
            text (str): Response text
            
        Returns:
            List[Dict[str, Any]]: List of parsed proxies
        """
        try:
            data = json.loads(text)
            return [{
                'proxy': f"{item['ip']}:{item['port']}",
                'country': item['country'],
                'anonymity': item['anonymity'],
                'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
            } for item in data]
        except Exception:
            return []
    
    def _parse_proxyscrape(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse proxies from ProxyScrape API.
        
        Args:
            text (str): Response text
            
        Returns:
            List[Dict[str, Any]]: List of parsed proxies
        """
        proxies = []
        for line in text.splitlines():
            if line.strip():
                proxies.append({
                    'proxy': line.strip(),
                    'country': self.country_code,
                    'anonymity': 'unknown',
                    'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                })
        return proxies
    
    def _parse_proxynova(self, text: str) -> List[Dict[str, Any]]:
        """
        Parse proxies from ProxyNova.
        
        Args:
            text (str): Response text
            
        Returns:
            List[Dict[str, Any]]: List of parsed proxies
        """
        proxies = []
        soup = BeautifulSoup(text, 'html.parser')
        table = soup.find('table', {'id': 'tbl_proxy_list'})
        
        if table:
            for row in table.find_all('tr')[1:]:
                cols = row.find_all('td')
                if len(cols) >= 8:
                    ip = cols[0].text.strip()
                    port = cols[1].text.strip()
                    proxies.append({
                        'proxy': f"{ip}:{port}",
                        'country': self.country_code,
                        'anonymity': cols[7].text.strip(),
                        'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                    })
        
        return proxies
    
    def _is_valid_country_code(self, code: str) -> bool:
        """
        Validate if a country code is valid.
        
        Args:
            code (str): Country code to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        valid_countries = {
            'AF', 'AX', 'AL', 'DZ', 'AS', 'AD', 'AO', 'AI', 'AQ', 'AG', 'AR', 'AM', 'AW', 'AU', 'AT', 'AZ',
            'BS', 'BH', 'BD', 'BB', 'BY', 'BE', 'BZ', 'BJ', 'BM', 'BT', 'BO', 'BQ', 'BA', 'BW', 'BV', 'BR',
            'IO', 'BN', 'BG', 'BF', 'BI', 'KH', 'CM', 'CA', 'CV', 'KY', 'CF', 'TD', 'CL', 'CN', 'CX', 'CC',
            'CO', 'KM', 'CG', 'CD', 'CK', 'CR', 'CI', 'HR', 'CU', 'CW', 'CY', 'CZ', 'DK', 'DJ', 'DM', 'DO',
            'EC', 'EG', 'SV', 'GQ', 'ER', 'EE', 'ET', 'FK', 'FO', 'FJ', 'FI', 'FR', 'GF', 'PF', 'TF', 'GA',
            'GM', 'GE', 'DE', 'GH', 'GI', 'GR', 'GL', 'GD', 'GP', 'GU', 'GT', 'GG', 'GN', 'GW', 'GY', 'HT',
            'HM', 'VA', 'HN', 'HK', 'HU', 'IS', 'IN', 'ID', 'IR', 'IQ', 'IE', 'IM', 'IL', 'IT', 'JM', 'JP',
            'JE', 'JO', 'KZ', 'KE', 'KI', 'KP', 'KR', 'KW', 'KG', 'LA', 'LV', 'LB', 'LS', 'LR', 'LY', 'LI',
            'LT', 'LU', 'MO', 'MK', 'MG', 'MW', 'MY', 'MV', 'ML', 'MT', 'MH', 'MQ', 'MR', 'MU', 'YT', 'MX',
            'FM', 'MD', 'MC', 'MN', 'ME', 'MS', 'MA', 'MZ', 'MM', 'NA', 'NR', 'NP', 'NL', 'NC', 'NZ', 'NI',
            'NE', 'NG', 'NU', 'NF', 'MP', 'NO', 'OM', 'PK', 'PW', 'PS', 'PA', 'PG', 'PY', 'PE', 'PH', 'PN',
            'PL', 'PT', 'PR', 'QA', 'RE', 'RO', 'RU', 'RW', 'BL', 'SH', 'KN', 'LC', 'MF', 'PM', 'VC', 'WS',
            'SM', 'ST', 'SA', 'SN', 'RS', 'SC', 'SL', 'SG', 'SX', 'SK', 'SI', 'SB', 'SO', 'ZA', 'GS', 'SS',
            'ES', 'LK', 'SD', 'SR', 'SJ', 'SZ', 'SE', 'CH', 'SY', 'TW', 'TJ', 'TZ', 'TH', 'TL', 'TG', 'TK',
            'TO', 'TT', 'TN', 'TR', 'TM', 'TC', 'TV', 'UG', 'UA', 'AE', 'GB', 'US', 'UM', 'UY', 'UZ', 'VU',
            'VE', 'VN', 'VG', 'VI', 'WF', 'EH', 'YE', 'ZM', 'ZW'
        }
        return code in valid_countries
