from typing import Optional, Dict, Any
import requests
import socket
import urllib3
import time
import datetime
import logging

# Setup logging
logger = logging.getLogger('proxy_finder')

class ProxyValidator:
    """Handles proxy validation and testing."""
    
    def __init__(self, 
                 timeout: float = 10.0, 
                 test_url: str = 'http://httpbin.org/ip'):
        """
        Initialize ProxyValidator with configurable settings.
        
        Args:
            timeout (float): Connection timeout in seconds. Defaults to 10.0.
            test_url (str): URL to test proxy connectivity. Defaults to httpbin.org.
        """
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        self.timeout = timeout
        self.test_url = test_url

    def validate_proxy(self, proxy: str) -> bool:
        """
        Validate a proxy by checking its connectivity.
        
        Args:
            proxy (str): Proxy URL in IP:PORT format.
        
        Returns:
            bool: True if proxy is valid, False otherwise.
        """
        try:
            # Use a reasonable timeout for validation
            validation_timeout = min(15.0, self.timeout)
            
            # Split the proxy into host and port
            host, port = proxy.split(':')
            
            # First just check if the socket is open (fast check)
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(validation_timeout / 2)  # Use half the timeout for socket check
                sock.connect((host, int(port)))
                sock.close()
                # If we can connect to the socket, consider it valid
                return True
            except (socket.timeout, socket.error) as e:
                logger.debug(f"Socket validation failed for proxy {proxy}: {e}")
                return False
        
        except Exception as e:
            logger.debug(f"Unexpected error during proxy validation for {proxy}: {e}")
            return False

    def get_proxy_details(self, proxy_data: Dict[str, Any] = None, proxy_str: str = None) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a proxy with quality metrics.
        Optimized for performance with more lenient validation.
        
        Args:
            proxy_data (Dict[str, Any], optional): Proxy data dictionary.
            proxy_str (str, optional): Proxy URL in IP:PORT format if proxy_data not provided.
        
        Returns:
            Optional[Dict[str, Any]]: Proxy details or None if validation fails.
        """
        # Get the proxy string from either input
        proxy = proxy_data.get('proxy') if proxy_data else proxy_str
        if not proxy:
            return None
            
        try:
            # Split the proxy into host and port
            host, port = proxy.split(':')
            
            # Socket check (fast pre-check)
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)  # Use a reasonable timeout for socket check
                sock.connect((host, int(port)))
                sock.close()
            except (socket.timeout, socket.error) as e:
                logger.debug(f"Socket connection failed for {proxy}: {e}")
                
                # LENIENT MODE: Still consider the proxy if we can at least open the socket
                # This is more forgiving but may include some non-functional proxies
                # We'll create a basic result dict with default values
                if proxy_data:
                    # Return a basic result with known data but mark as unvalidated
                    return {
                        'proxy': proxy,
                        'status': 'unvalidated',
                        'speed': 999.99,
                        'last_checked': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'ip': proxy.split(':')[0],
                        'country': proxy_data.get('country', 'unknown'),
                        'anonymity': proxy_data.get('anonymity', 'unknown'),
                        'requires_auth': False
                    }
                return None
            
            # If socket is open, configure proxy settings
            proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            
            # Test URLs to try in order - now all using HTTP for better compatibility
            test_urls = [
                'http://httpbin.org/ip',             # Most reliable
                'http://ip-api.com/json',            # Good alternative
                'http://ifconfig.me/ip',             # Simple IP service
                'http://example.com',                # Very basic site
                'http://www.google.com'              # Last resort
            ]
            
            # Try each test URL until one works
            response = None
            response_time = 0
            auth_required = False
            
            for test_url in test_urls:
                try:
                    logger.debug(f"Testing proxy {proxy} with URL {test_url}")
                    # Measure response time
                    start_time = time.time()
                    
                    # Use a shorter timeout for the HTTP request
                    response = requests.get(
                        test_url, 
                        proxies=proxies, 
                        timeout=min(8.0, self.timeout),
                        verify=False,                # Skip SSL verification
                        allow_redirects=True         # Follow redirects
                    )
                    
                    # Calculate response time
                    response_time = time.time() - start_time
                    
                    # Check if proxy requires authentication (status code 407)
                    if response.status_code == 407:
                        auth_required = True
                        logger.debug(f"Proxy {proxy} requires authentication")
                        break
                    
                    if response.status_code == 200:
                        logger.debug(f"Proxy {proxy} validated successfully with {test_url}")
                        break
                except Exception as e:
                    logger.debug(f"Error testing {proxy} with {test_url}: {e}")
                    continue
            
            # Create result dictionary
            result = {
                'proxy': proxy,
                'status': 'valid' if response and response.status_code == 200 else 'unvalidated',
                'speed': round(response_time, 2) if response else 999.99,
                'last_checked': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'ip': proxy.split(':')[0],  # Default to the proxy IP
                'requires_auth': auth_required
            }
            
            # If we got a successful HTTP response, enhance the result with more details
            if response and response.status_code == 200:
                # Try to get the IP, but don't fail if we can't
                try:
                    # Different APIs return IP in different formats
                    if 'origin' in response.text:
                        result['ip'] = response.json().get('origin')
                    elif 'query' in response.text:
                        result['ip'] = response.json().get('query')
                    elif len(response.text.strip()) < 20:  # Simple IP response
                        result['ip'] = response.text.strip()
                except Exception as e:
                    logger.debug(f"Error parsing IP from response for {proxy}: {e}")
                    pass  # Keep the default IP
            
            # Add country and anonymity if available in proxy_data
            if proxy_data:
                result['country'] = proxy_data.get('country', 'unknown')
                result['anonymity'] = proxy_data.get('anonymity', 'unknown')
            else:
                result['country'] = 'unknown'
                result['anonymity'] = 'unknown'
            
            # Only check anonymity if we don't already have it
            if result['anonymity'] == 'unknown' and response:
                # Use a simplified check for speed
                if response_time < 2.0:
                    result['anonymity'] = 'elite'  # Fast proxies are often elite
                elif response_time < 5.0:
                    result['anonymity'] = 'anonymous'  # Medium speed proxies are often anonymous
                else:
                    result['anonymity'] = 'transparent'  # Slow proxies are often transparent
            
            logger.debug(f"Proxy details for {proxy}: {result}")
            return result
        
        except Exception as e:
            logger.warning(f"Error getting proxy details for {proxy}: {e}")
            return None
            
    def _check_anonymity_level(self, proxy: str) -> str:
        """
        Simplified check for the anonymity level of a proxy.
        For performance reasons, we'll use a simplified approach.
        
        Args:
            proxy (str): Proxy URL in IP:PORT format.
            
        Returns:
            str: Anonymity level ('transparent', 'anonymous', 'elite', or 'unknown').
        """
        # For performance reasons, we'll use a simplified approach
        # This is much faster but less accurate
        try:
            # Use a shorter timeout
            short_timeout = min(2.0, self.timeout)
            
            proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            
            # Quick check with a simple URL
            response = requests.get(
                'http://httpbin.org/headers',  # Use HTTP instead of HTTPS for speed
                proxies=proxies,
                timeout=short_timeout,
                verify=False
            )
            
            if response.status_code == 200:
                # Simplified check based on common headers
                headers = response.json().get('headers', {})
                
                # Check for the most important header
                if 'X-Forwarded-For' not in headers and 'Via' not in headers:
                    return 'elite'
                elif 'X-Forwarded-For' not in headers:
                    return 'anonymous'
                else:
                    return 'transparent'
        except Exception as e:
            logger.debug(f"Error checking anonymity level for {proxy}: {e}")
            pass
            
        # Default to unknown
        return 'unknown'
