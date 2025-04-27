from typing import List, Dict, Any, Optional, Set
import requests
import json
import time
import concurrent.futures
import re
import logging
from bs4 import BeautifulSoup

from ..exceptions import ProxyFetchError

# Setup logging
logger = logging.getLogger('proxy_finder')

class ProxyFetcher:
    """Enhanced proxy fetcher with advanced country support."""
    
    def __init__(self, country: str = None, timeout: float = 5.0, max_sources: int = 5):
        """
        Initialize ProxyFetcher with optional country filter.
        
        Args:
            country (str, optional): Two-letter country code to filter proxies (e.g., 'US', 'GB').
            timeout (float): Timeout for requests in seconds. Defaults to 5.0.
            max_sources (int): Maximum number of sources to query. Defaults to 5.
        """
        self.country = country and country.upper()
        self.timeout = timeout
        self.max_sources = max_sources
        
        # Cache for IP geolocation data
        self.geo_cache = {}
        
        # Country name to code mapping
        self.country_map = self._build_country_map()
        
        # Build sources with prioritization
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
            'belgium': 'BE', 'austria': 'AT', 'portugal': 'PT', 'greece': 'GR',
            'czech republic': 'CZ', 'romania': 'RO', 'hungary': 'HU', 'bulgaria': 'BG',
            'serbia': 'RS', 'croatia': 'HR', 'slovakia': 'SK', 'slovenia': 'SI',
            'estonia': 'EE', 'latvia': 'LV', 'lithuania': 'LT', 'belarus': 'BY',
            'kazakhstan': 'KZ', 'taiwan': 'TW', 'hong kong': 'HK', 'israel': 'IL',
            'saudi arabia': 'SA', 'united arab emirates': 'AE', 'new zealand': 'NZ',
            'philippines': 'PH', 'chile': 'CL', 'colombia': 'CO', 'peru': 'PE',
            'venezuela': 'VE', 'bangladesh': 'BD', 'nigeria': 'NG', 'kenya': 'KE',
            'morocco': 'MA', 'algeria': 'DZ', 'tunisia': 'TN', 'iran': 'IR',
            'iraq': 'IQ', 'syria': 'SY', 'jordan': 'JO', 'lebanon': 'LB',
            'kuwait': 'KW', 'qatar': 'QA', 'bahrain': 'BH', 'oman': 'OM',
            'yemen': 'YE', 'afghanistan': 'AF', 'nepal': 'NP', 'sri lanka': 'LK',
            'myanmar': 'MM', 'cambodia': 'KH', 'laos': 'LA', 'mongolia': 'MN',
            'north korea': 'KP', 'uzbekistan': 'UZ', 'turkmenistan': 'TM',
            'kyrgyzstan': 'KG', 'tajikistan': 'TJ', 'azerbaijan': 'AZ',
            'armenia': 'AM', 'georgia': 'GE', 'cyprus': 'CY', 'malta': 'MT',
            'iceland': 'IS', 'luxembourg': 'LU', 'monaco': 'MC', 'liechtenstein': 'LI',
            'andorra': 'AD', 'san marino': 'SM', 'vatican city': 'VA'
        }
    
    def _build_sources(self) -> List[Dict[str, Any]]:
        """Build a list of proxy sources with metadata."""
        sources = [
            {
                'name': 'proxyscrape',
                'url': f'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country={self.country or "all"}&ssl=all&anonymity=all',
                'parser': self._parse_text_list,
                'priority': 1,
                'supports_country': True
            },
            {
                'name': 'geonode',
                'url': f'https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc{f"&country={self.country}" if self.country else ""}',
                'parser': self._parse_geonode,
                'priority': 1,
                'supports_country': True
            },
            {
                'name': 'proxy-list',
                'url': 'https://www.proxy-list.download/api/v1/get?type=http',
                'parser': self._parse_text_list,
                'priority': 2,
                'supports_country': False
            },
            {
                'name': 'speedx',
                'url': 'https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt',
                'parser': self._parse_text_list,
                'priority': 2,
                'supports_country': False
            },
            {
                'name': 'shifty',
                'url': 'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
                'parser': self._parse_text_list,
                'priority': 2,
                'supports_country': False
            },
            {
                'name': 'jetkai',
                'url': 'https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt',
                'parser': self._parse_text_list,
                'priority': 2,
                'supports_country': False
            },
            {
                'name': 'mmpx12',
                'url': 'https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt',
                'parser': self._parse_text_list,
                'priority': 3,
                'supports_country': False
            },
            {
                'name': 'proxyscan',
                'url': f'https://www.proxyscan.io/api/proxy?format=json&type=http&limit=100{f"&country={self.country}" if self.country else ""}',
                'parser': self._parse_proxyscan,
                'priority': 3,
                'supports_country': True
            },
            {
                'name': 'proxydb',
                'url': 'http://proxydb.net/',
                'parser': self._parse_proxydb,
                'priority': 4,
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
    
    def fetch_proxies(self) -> List[Dict[str, Any]]:
        """
        Fetch proxies from multiple sources concurrently.
        
        Returns:
            List[Dict[str, Any]]: List of proxy dictionaries with metadata.
        
        Raises:
            ProxyFetchError: If no proxies could be fetched from any source.
        """
        all_proxies = []
        
        # Use ThreadPoolExecutor for concurrent fetching
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(self.sources), 5)) as executor:
            future_to_source = {
                executor.submit(self._fetch_from_source, source): source
                for source in self.sources
            }
            
            for future in concurrent.futures.as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    proxies = future.result()
                    all_proxies.extend(proxies)
                    logger.info(f"Fetched {len(proxies)} proxies from {source['name']}")
                except Exception as e:
                    logger.warning(f"Error fetching from {source['name']}: {e}")
        
        if not all_proxies:
            raise ProxyFetchError("No proxies could be fetched from any source")
        
        # Remove duplicates and apply country filter
        unique_proxies = self._filter_and_deduplicate(all_proxies)
        
        # Limit to a reasonable number for performance
        return unique_proxies[:100]
    
    def _fetch_from_source(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch proxies from a single source.
        
        Args:
            source (Dict[str, Any]): Source configuration.
            
        Returns:
            List[Dict[str, Any]]: List of proxy dictionaries from this source.
        """
        try:
            response = requests.get(source['url'], timeout=self.timeout)
            response.raise_for_status()
            
            # Parse the response using the source's parser
            return source['parser'](response.text, source['name'])
        
        except Exception as e:
            logger.warning(f"Error fetching from {source['name']}: {e}")
            return []
    
    def _parse_text_list(self, text: str, source_name: str) -> List[Dict[str, Any]]:
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
                # Validate proxy format (IP:PORT)
                if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}$', line):
                    country = self._get_proxy_country(line)
                    
                    # Skip if country filter is active and doesn't match
                    if self.country and country != self.country:
                        continue
                        
                    result.append({
                        'proxy': line,
                        'country': country,
                        'anonymity': 'unknown',
                        'source': source_name,
                        'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                    })
        return result
    
    def _parse_geonode(self, text: str, source_name: str) -> List[Dict[str, Any]]:
        """
        Parse proxies from GeoNode API.
        
        Args:
            text (str): JSON response from GeoNode API.
            source_name (str): Name of the source for logging.
            
        Returns:
            List[Dict[str, Any]]: List of proxy dictionaries.
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
                        'last_checked': item.get('last_checked', time.strftime('%Y-%m-%d %H:%M:%S'))
                    })
        except Exception as e:
            logger.warning(f"Error parsing GeoNode response: {e}")
        return result
    
    def _parse_proxyscan(self, text: str, source_name: str) -> List[Dict[str, Any]]:
        """
        Parse proxies from ProxyScan API.
        
        Args:
            text (str): JSON response from ProxyScan API.
            source_name (str): Name of the source for logging.
            
        Returns:
            List[Dict[str, Any]]: List of proxy dictionaries.
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
    
    def _parse_proxydb(self, text: str, source_name: str) -> List[Dict[str, Any]]:
        """
        Parse proxies from ProxyDB website.
        
        Args:
            text (str): HTML content from ProxyDB.
            source_name (str): Name of the source for logging.
            
        Returns:
            List[Dict[str, Any]]: List of proxy dictionaries.
        """
        result = []
        try:
            soup = BeautifulSoup(text, 'html.parser')
            table = soup.find('table', {'id': 'proxydb'})
            
            if table:
                rows = table.find_all('tr')
                for row in rows[1:]:  # Skip header row
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        ip_port = cells[0].text.strip()
                        country_cell = cells[1]
                        
                        # Extract country code from the flag image or text
                        country_code = 'unknown'
                        country_img = country_cell.find('img')
                        if country_img and 'alt' in country_img.attrs:
                            country_name = country_img['alt'].lower()
                            country_code = self.country_map.get(country_name, 'unknown')
                        
                        # Skip if country filter is active and doesn't match
                        if self.country and country_code != self.country:
                            continue
                            
                        result.append({
                            'proxy': ip_port,
                            'country': country_code,
                            'anonymity': 'unknown',
                            'source': source_name,
                            'last_checked': time.strftime('%Y-%m-%d %H:%M:%S')
                        })
        except Exception as e:
            logger.warning(f"Error parsing ProxyDB response: {e}")
        return result
    
    def _filter_and_deduplicate(self, proxies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter and deduplicate proxies.
        
        Args:
            proxies (List[Dict[str, Any]]): List of proxy dictionaries.
            
        Returns:
            List[Dict[str, Any]]: Filtered and deduplicated proxy list.
        """
        # Remove duplicates based on proxy IP:PORT
        unique_proxies = []
        seen = set()
        
        for proxy_data in proxies:
            proxy_str = proxy_data['proxy']
            
            # Basic format validation
            if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}$', proxy_str):
                continue
                
            # Deduplicate
            if proxy_str not in seen:
                seen.add(proxy_str)
                
                # Apply country filter if specified
                if self.country and proxy_data.get('country') != self.country:
                    continue
                    
                unique_proxies.append(proxy_data)
        
        return unique_proxies
    
    def _get_proxy_country(self, proxy: str) -> str:
        """
        Get country for a proxy using IP geolocation or pattern matching.
        
        Args:
            proxy (str): Proxy in IP:PORT format.
        
        Returns:
            str: Two-letter country code or 'unknown'.
        """
        # Return from cache if available
        if proxy in self.geo_cache:
            return self.geo_cache[proxy]
            
        # If country filtering is active, assume all proxies match the filter
        if self.country:
            self.geo_cache[proxy] = self.country
            return self.country
            
        # Use pattern matching for common IP ranges
        try:
            ip = proxy.split(':')[0]
            
            # Common IP patterns and their likely countries
            country_patterns = {
                r'^104\.16\.': 'US',  # Cloudflare
                r'^104\.17\.': 'US',  # Cloudflare
                r'^5\.': 'DE',        # German IPs often start with 5
                r'^46\.': 'DE',       # German IPs often start with 46
                r'^185\.': 'RU',      # Russian IPs often start with 185
                r'^95\.': 'RU',       # Russian IPs often start with 95
                r'^103\.': 'IN',      # Indian IPs often start with 103
                r'^45\.': 'BR',       # Brazilian IPs often start with 45
                r'^139\.': 'JP',      # Japanese IPs often start with 139
                r'^202\.': 'SG',      # Singapore IPs often start with 202
                r'^203\.': 'AU',      # Australian IPs often start with 203
                r'^213\.': 'GB',      # UK IPs often start with 213
                r'^195\.': 'FR',      # French IPs often start with 195
                r'^91\.': 'NL',       # Dutch IPs often start with 91
                r'^200\.': 'MX',      # Mexican IPs often start with 200
                r'^201\.': 'MX',      # Mexican IPs often start with 201
                r'^190\.': 'AR',      # Argentinian IPs often start with 190
                r'^186\.': 'CO',      # Colombian IPs often start with 186
                r'^187\.': 'BR',      # Brazilian IPs often start with 187
                r'^189\.': 'BR',      # Brazilian IPs often start with 189
                r'^14\.': 'KR',       # South Korean IPs often start with 14
                r'^101\.': 'TW',      # Taiwan IPs often start with 101
                r'^1\.': 'CN',        # Chinese IPs often start with 1
                r'^116\.': 'CN',      # Chinese IPs often start with 116
                r'^118\.': 'CN',      # Chinese IPs often start with 118
                r'^121\.': 'CN',      # Chinese IPs often start with 121
                r'^122\.': 'CN',      # Chinese IPs often start with 122
                r'^123\.': 'CN',      # Chinese IPs often start with 123
                r'^124\.': 'CN',      # Chinese IPs often start with 124
                r'^125\.': 'CN',      # Chinese IPs often start with 125
                r'^222\.': 'CN',      # Chinese IPs often start with 222
                r'^223\.': 'CN',      # Chinese IPs often start with 223
                r'^58\.': 'CN',       # Chinese IPs often start with 58
                r'^59\.': 'CN',       # Chinese IPs often start with 59
                r'^60\.': 'CN',       # Chinese IPs often start with 60
                r'^61\.': 'CN',       # Chinese IPs often start with 61
                r'^111\.': 'KR',      # South Korean IPs often start with 111
                r'^112\.': 'KR',      # South Korean IPs often start with 112
                r'^211\.': 'KR',      # South Korean IPs often start with 211
                r'^175\.': 'SG',      # Singapore IPs often start with 175
                r'^119\.': 'SG',      # Singapore IPs often start with 119
                r'^128\.': 'US',      # US IPs often start with 128
                r'^129\.': 'US',      # US IPs often start with 129
                r'^130\.': 'US',      # US IPs often start with 130
                r'^131\.': 'US',      # US IPs often start with 131
                r'^132\.': 'US',      # US IPs often start with 132
                r'^134\.': 'US',      # US IPs often start with 134
                r'^135\.': 'US',      # US IPs often start with 135
                r'^136\.': 'US',      # US IPs often start with 136
                r'^137\.': 'US',      # US IPs often start with 137
                r'^138\.': 'US',      # US IPs often start with 138
                r'^142\.': 'US',      # US IPs often start with 142
                r'^143\.': 'US',      # US IPs often start with 143
                r'^144\.': 'US',      # US IPs often start with 144
                r'^146\.': 'US',      # US IPs often start with 146
                r'^147\.': 'US',      # US IPs often start with 147
                r'^148\.': 'US',      # US IPs often start with 148
                r'^149\.': 'US',      # US IPs often start with 149
                r'^152\.': 'US',      # US IPs often start with 152
                r'^153\.': 'US',      # US IPs often start with 153
                r'^154\.': 'US',      # US IPs often start with 154
                r'^155\.': 'US',      # US IPs often start with 155
                r'^156\.': 'US',      # US IPs often start with 156
                r'^157\.': 'US',      # US IPs often start with 157
                r'^158\.': 'US',      # US IPs often start with 158
                r'^159\.': 'US',      # US IPs often start with 159
                r'^160\.': 'US',      # US IPs often start with 160
                r'^161\.': 'US',      # US IPs often start with 161
                r'^162\.': 'US',      # US IPs often start with 162
                r'^164\.': 'US',      # US IPs often start with 164
                r'^165\.': 'US',      # US IPs often start with 165
                r'^166\.': 'US',      # US IPs often start with 166
                r'^167\.': 'US',      # US IPs often start with 167
                r'^168\.': 'US',      # US IPs often start with 168
                r'^169\.': 'US',      # US IPs often start with 169
                r'^170\.': 'US',      # US IPs often start with 170
                r'^171\.': 'US',      # US IPs often start with 171
                r'^172\.': 'US',      # US IPs often start with 172
                r'^173\.': 'US',      # US IPs often start with 173
                r'^174\.': 'US',      # US IPs often start with 174
                r'^192\.': 'US',      # US IPs often start with 192
                r'^198\.': 'US',      # US IPs often start with 198
                r'^199\.': 'US',      # US IPs often start with 199
                r'^204\.': 'US',      # US IPs often start with 204
                r'^205\.': 'US',      # US IPs often start with 205
                r'^206\.': 'US',      # US IPs often start with 206
                r'^207\.': 'US',      # US IPs often start with 207
                r'^208\.': 'US',      # US IPs often start with 208
                r'^209\.': 'US',      # US IPs often start with 209
                r'^216\.': 'US',      # US IPs often start with 216
                r'^63\.': 'US',       # US IPs often start with 63
                r'^64\.': 'US',       # US IPs often start with 64
                r'^65\.': 'US',       # US IPs often start with 65
                r'^66\.': 'US',       # US IPs often start with 66
                r'^67\.': 'US',       # US IPs often start with 67
                r'^68\.': 'US',       # US IPs often start with 68
                r'^69\.': 'US',       # US IPs often start with 69
                r'^70\.': 'US',       # US IPs often start with 70
                r'^71\.': 'US',       # US IPs often start with 71
                r'^72\.': 'US',       # US IPs often start with 72
                r'^73\.': 'US',       # US IPs often start with 73
                r'^74\.': 'US',       # US IPs often start with 74
                r'^75\.': 'US',       # US IPs often start with 75
                r'^76\.': 'US',       # US IPs often start with 76
                r'^96\.': 'US',       # US IPs often start with 96
                r'^97\.': 'US',       # US IPs often start with 97
                r'^98\.': 'US',       # US IPs often start with 98
                r'^99\.': 'US',       # US IPs often start with 99
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
    
    def get_available_countries(self) -> Dict[str, str]:
        """
        Get a list of available countries with their codes.
        
        Returns:
            Dict[str, str]: Dictionary mapping country codes to country names.
        """
        # Invert the country map for code to name mapping
        code_to_name = {}
        for name, code in self.country_map.items():
            if code not in code_to_name:
                # Capitalize the first letter of each word
                code_to_name[code] = ' '.join(word.capitalize() for word in name.split())
        
        return code_to_name
