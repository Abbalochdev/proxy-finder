from typing import List, Dict, Any, Optional
import re

class ProxyFilter:
    """Handles filtering and cleaning of proxy lists."""
    
    def __init__(self, 
                 min_anonymity: str = 'anonymous', 
                 protocols: Optional[List[str]] = None):
        """
        Initialize ProxyFilter with filtering criteria.
        
        Args:
            min_anonymity (str): Minimum anonymity level. Defaults to 'anonymous'.
            protocols (Optional[List[str]]): Allowed protocols. Defaults to HTTP/HTTPS.
        """
        self.min_anonymity = min_anonymity
        self.protocols = protocols or ['http', 'https']

    def filter_proxies(self, proxies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter and clean proxy list based on configured criteria.
        
        Args:
            proxies (List[Dict[str, Any]]): List of proxy dictionaries.
        
        Returns:
            List[Dict[str, Any]]: Filtered and cleaned proxy list.
        """
        filtered_proxies = []
        
        for proxy_data in proxies:
            proxy_str = proxy_data.get('proxy', '')
            
            # Basic format validation
            if not self._is_valid_proxy_format(proxy_str):
                continue
                
            # Filter by anonymity if specified
            if self.min_anonymity != 'anonymous':
                anonymity = proxy_data.get('anonymity', 'unknown')
                if anonymity == 'transparent' and self.min_anonymity in ['anonymous', 'elite']:
                    continue
                if anonymity == 'anonymous' and self.min_anonymity == 'elite':
                    continue
            
            # Optional: Add more sophisticated filtering here
            filtered_proxies.append(proxy_data)
        
        return filtered_proxies

    def _is_valid_proxy_format(self, proxy: str) -> bool:
        """
        Validate proxy string format.
        
        Args:
            proxy (str): Proxy string to validate.
        
        Returns:
            bool: True if proxy format is valid, False otherwise.
        """
        # Regex for IP:PORT format
        proxy_pattern = r'^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{2,5})$'
        
        if not re.match(proxy_pattern, proxy):
            return False
        
        # Optional: Add IP and port range validation
        ip_parts = proxy.split(':')[0].split('.')
        port = int(proxy.split(':')[1])
        
        # Validate IP address
        if any(int(part) < 0 or int(part) > 255 for part in ip_parts):
            return False
        
        # Validate port range
        if port < 1 or port > 65535:
            return False
        
        return True
