import os
import json
import time
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger('proxy_finder')

class ProxyStorage:
    """
    Manages storage and retrieval of validated proxies for reuse.
    """
    
    def __init__(self, cache_dir: str = None):
        """
        Initialize proxy storage.
        
        Args:
            cache_dir (str, optional): Directory to store proxy cache files.
                Defaults to ~/.proxy_finder/cache.
        """
        if not cache_dir:
            home_dir = os.path.expanduser("~")
            cache_dir = os.path.join(home_dir, ".proxy_finder", "cache")
            
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(self.cache_dir, "proxy_cache.json")
        self._ensure_cache_dir()
        
    def _ensure_cache_dir(self):
        """Create cache directory if it doesn't exist."""
        if not os.path.exists(self.cache_dir):
            try:
                os.makedirs(self.cache_dir, exist_ok=True)
                logger.info(f"Created cache directory: {self.cache_dir}")
            except Exception as e:
                logger.warning(f"Failed to create cache directory: {e}")
                
    def save_proxies(self, proxies: List[Dict[str, Any]]):
        """
        Save validated proxies to the cache file.
        
        Args:
            proxies (List[Dict[str, Any]]): List of proxy dictionaries.
        """
        try:
            self._ensure_cache_dir()
            
            # Add timestamp to each proxy
            for proxy in proxies:
                proxy['cached_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
            
            with open(self.cache_file, 'w') as f:
                json.dump(proxies, f, indent=2)
                
            logger.info(f"Saved {len(proxies)} proxies to cache")
        except Exception as e:
            logger.warning(f"Failed to save proxies to cache: {e}")
            
    def load_proxies(self, max_age_hours: int = 24) -> List[Dict[str, Any]]:
        """
        Load proxies from the cache file, filtering by age.
        
        Args:
            max_age_hours (int): Maximum age of cache in hours. Defaults to 24.
            
        Returns:
            List[Dict[str, Any]]: List of cached proxy dictionaries.
        """
        proxies = []
        
        try:
            if not os.path.exists(self.cache_file):
                logger.info("No proxy cache file exists")
                return []
                
            with open(self.cache_file, 'r') as f:
                cached_proxies = json.load(f)
                
            # Filter by age
            now = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for proxy in cached_proxies:
                try:
                    cache_time_str = proxy.get('cached_at')
                    if not cache_time_str:
                        continue
                        
                    cache_time = time.mktime(time.strptime(cache_time_str, '%Y-%m-%d %H:%M:%S'))
                    age = now - cache_time
                    
                    if age <= max_age_seconds:
                        proxies.append(proxy)
                except Exception:
                    continue
                    
            logger.info(f"Loaded {len(proxies)} valid proxies from cache (out of {len(cached_proxies)} total)")
        except Exception as e:
            logger.warning(f"Failed to load proxies from cache: {e}")
            
        return proxies 