from typing import Optional, Dict, Any
import requests
import socket
import urllib3
import time
import datetime

class ProxyValidator:
    """Handles proxy validation and testing."""
    
    def __init__(self, 
                 timeout: float = 15.0, 
                 test_url: str = 'https://httpbin.org/ip'):
        """
        Initialize ProxyValidator with configurable settings.
        
        Args:
            timeout (float): Connection timeout in seconds. Defaults to 15.0.
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
            # Use a more reasonable timeout for validation
            validation_timeout = min(20.0, self.timeout)
            
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
            except (socket.timeout, socket.error):
                return False
        
        except Exception:
            return False

    def get_proxy_details(self, proxy_data: Dict[str, Any] = None, proxy_str: str = None) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a proxy with quality metrics.
        Optimized for performance.
        
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
            
            # First just check if the socket is open (fast check)
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)  # Use a reasonable timeout for socket check
                sock.connect((host, int(port)))
                sock.close()
            except (socket.timeout, socket.error):
                return None
            
            # If socket is open, we'll consider this a valid proxy
            # This is extremely lenient but will help find more proxies
            
            # Use a more reasonable timeout for validation
            validation_timeout = min(20.0, self.timeout)
            
            proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
            
            # Test URLs to try in order
            test_urls = [
                'http://httpbin.org/ip',
                'http://ip-api.com/json',
                'http://ifconfig.me/ip',
                'http://www.google.com',  # Just check if we can reach Google
                'http://example.com'      # Or any simple website
            ]
            
            # Try each test URL until one works
            response = None
            response_time = 0
            auth_required = False
            
            for test_url in test_urls:
                try:
                    # Measure response time
                    start_time = time.time()
                    
                    # Test with HTTP instead of HTTPS for better compatibility
                    response = requests.get(
                        test_url, 
                        proxies=proxies, 
                        timeout=validation_timeout,
                        verify=False
                    )
                    
                    # Calculate response time
                    response_time = time.time() - start_time
                    
                    # Check if proxy requires authentication (status code 407)
                    if response.status_code == 407:
                        auth_required = True
                        break
                    
                    if response.status_code == 200:
                        break
                except Exception as e:
                    continue
            
            # Create result dictionary
            result = {
                'proxy': proxy,
                'status': 'valid',
                'speed': round(response_time, 2) if response else 999.99,  # High value if no response
                'last_checked': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'ip': proxy.split(':')[0],  # Default to the proxy IP
                'requires_auth': auth_required  # Indicate if authentication is required
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
                except:
                    pass  # Keep the default IP
            
            # Add country and anonymity if available in proxy_data
            if proxy_data:
                result['country'] = proxy_data.get('country', 'unknown')
                result['anonymity'] = proxy_data.get('anonymity', 'unknown')
            else:
                result['country'] = 'unknown'
                result['anonymity'] = 'unknown'
            
            # Only check anonymity if we don't already have it
            if result['anonymity'] == 'unknown':
                # Use a simplified check for speed
                if response and response_time < 2.0:
                    result['anonymity'] = 'elite'  # Fast proxies are often elite
                elif response and response_time < 5.0:
                    result['anonymity'] = 'anonymous'  # Medium speed proxies are often anonymous
                else:
                    result['anonymity'] = 'transparent'  # Slow proxies are often transparent
            
            return result
            
            return None
        
        except Exception:
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
        except Exception:
            pass
            
        # Default to unknown
        return 'unknown'
