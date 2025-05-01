from typing import List, Dict, Any, Optional
import logging
import random

from ..utils.logging import setup_logging
from .enhanced_fetcher import ProxyFetcher
from .filter import ProxyFilter
from .validator import ProxyValidator
from ..exceptions import ProxyFinderError

class ProxyManager:
    def __init__(self, 
                 max_retries: int = 3, 
                 timeout: float = 10.0,
                 country: str = None,
                 countries: List[str] = None,
                 anonymity: str = None):
        """
        Initialize ProxyManager with configurable settings.
        
        Args:
            max_retries (int): Maximum number of retry attempts. Defaults to 3.
            timeout (float): Connection timeout in seconds. Defaults to 10.0.
            country (str, optional): Two-letter country code to filter proxies (e.g., 'US', 'GB').
            countries (List[str], optional): List of country codes to fetch proxies from.
            anonymity (str, optional): Anonymity level to filter by ('transparent', 'anonymous', 'elite').
        """
        self.logger = setup_logging()
        self.fetcher = ProxyFetcher(country=country, timeout=timeout)
        self.filter = ProxyFilter()
        self.validator = ProxyValidator(timeout=timeout)
        self.max_retries = max_retries
        self.country = country
        self.countries = countries or ([country] if country else None)
        self.anonymity = anonymity
        self.proxy_cache = {}
        self.static_fetcher = ProxyFetcher(country=None, timeout=timeout)

    def get_proxy(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve a valid proxy after filtering and validation.
        
        Returns:
            Optional[Dict[str, Any]]: A valid proxy with details or None if no proxy found.
        
        Raises:
            ProxyFinderError: If proxy retrieval fails after max retries.
        """
        for attempt in range(self.max_retries):
            try:
                # Try each country if multiple countries are specified
                if self.countries and len(self.countries) > 1:
                    for country in self.countries:
                        try:
                            # Create a temporary fetcher for this specific country
                            country_fetcher = ProxyFetcher(country=country, timeout=self.validator.timeout)
                            proxy_list = country_fetcher.fetch_proxies()
                            
                            # Apply additional filtering if needed
                            if self.anonymity:
                                proxy_list = [p for p in proxy_list if p.get('anonymity') == self.anonymity]
                            
                            # Validate proxies
                            for proxy_data in proxy_list:
                                proxy_details = self.validator.get_proxy_details(proxy_data=proxy_data)
                                if proxy_details:
                                    self.logger.info(f"Found valid proxy from {country}: {proxy_details['proxy']}")
                                    return proxy_details
                        except Exception as e:
                            self.logger.warning(f"Error fetching from {country}: {e}")
                else:
                    # Fetch proxies with country filter if specified
                    proxy_list = self.fetcher.fetch_proxies()
                    
                    # Apply additional filtering if needed
                    if self.anonymity:
                        proxy_list = [p for p in proxy_list if p.get('anonymity') == self.anonymity]
                    
                    # Validate proxies
                    for proxy_data in proxy_list:
                        proxy_details = self.validator.get_proxy_details(proxy_data=proxy_data)
                        if proxy_details:
                            self.logger.info(f"Found valid proxy: {proxy_details['proxy']}")
                            return proxy_details
                
                # Validate static proxies
                for proxy_data in static_proxies:
                    proxy_str = proxy_data.get('proxy')
                    
                    # Check cache first
                    if proxy_str in self.proxy_cache:
                        self.logger.info(f"Using cached static proxy: {proxy_str}")
                        return self.proxy_cache[proxy_str]
                    
                    proxy_details = self.validator.get_proxy_details(proxy_data=proxy_data)
                    if proxy_details:
                        self.logger.info(f"Found valid static proxy: {proxy_details['proxy']}")
                        # Cache the proxy
                        self.proxy_cache[proxy_str] = proxy_details
                        return proxy_details
                
                self.logger.warning(f"No valid proxies found in attempt {attempt + 1}")
            
            except Exception as e:
                self.logger.error(f"Proxy retrieval error: {e}")
        
        raise ProxyFinderError("Failed to retrieve a valid proxy after maximum retries.")

    def rotate_proxies(self, num_proxies: int = 5, max_attempts: int = 10, timeout: float = 5.0, countries: List[str] = None) -> List[dict]:
        """
        Retrieve multiple valid proxies with quality metrics.
        
        Args:
            num_proxies (int): Number of proxies to retrieve. Defaults to 5.
            max_attempts (int): Maximum number of attempts per proxy. Defaults to 10.
            timeout (float): Timeout for proxy validation in seconds. Defaults to 5.0.
            countries (List[str], optional): List of country codes to fetch proxies from.
                                            Overrides the countries set in the constructor.
        
        Returns:
            List[dict]: List of proxy information dictionaries containing:
                - proxy: str - The proxy URL
                - speed: float - Response time in seconds
                - anonymity: str - Anonymity level
                - country: str - Country code
                - last_checked: str - Timestamp of last check
        """
        valid_proxies = []
        attempts = 0
        seen_proxies = set()
        
        # Use countries from parameter or instance variable
        target_countries = countries or self.countries

        # Loop until we have enough proxies or reach max attempts
        while len(valid_proxies) < num_proxies and attempts < max_attempts * num_proxies:
            try:
                self.logger.info(f"Rotation attempt {attempts + 1}/{max_attempts * num_proxies}, found {len(valid_proxies)}/{num_proxies} proxies")
                
                all_proxies = []
                
                # If multiple countries are specified, fetch from each
                if target_countries and len(target_countries) > 1:
                    for country_code in target_countries:
                        try:
                            # Create a temporary fetcher for this country
                            country_fetcher = ProxyFetcher(country=country_code, timeout=timeout)
                            country_proxies = country_fetcher.fetch_proxies()
                            all_proxies.extend(country_proxies)
                            self.logger.info(f"Fetched {len(country_proxies)} proxies from {country_code}")
                        except Exception as e:
                            self.logger.warning(f"Error fetching from {country_code}: {e}")
                else:
                    # Use the main fetcher
                    try:
                        all_proxies = self.fetcher.fetch_proxies()
                    except Exception as e:
                        self.logger.warning(f"Error fetching with main fetcher: {e}")
                        
                        # Try static fetcher as fallback if we have few proxies
                        if len(valid_proxies) < num_proxies / 2:
                            self.logger.info("Using static fetcher as fallback")
                            try:
                                static_proxies = self.static_fetcher.fetch_proxies()
                                all_proxies.extend(static_proxies)
                            except Exception as static_e:
                                self.logger.warning(f"Error with static fetcher: {static_e}")
                
                # Filter out already seen proxies
                new_proxies = [p for p in all_proxies if p.get('proxy') not in seen_proxies]
                if not new_proxies:
                    self.logger.warning("No new proxies available")
                    attempts += 1
                    # If we're on our last few attempts, retry some seen proxies randomly
                    if attempts > max_attempts * num_proxies * 0.8 and all_proxies:
                        # Take some random proxies to retry
                        random_selection = random.sample(all_proxies, min(10, len(all_proxies)))
                        new_proxies = random_selection
                        self.logger.info(f"Retrying {len(new_proxies)} previously seen proxies")
                    else:
                        continue

                for proxy_data in new_proxies:
                    proxy_str = proxy_data.get('proxy')
                    if not proxy_str:
                        continue
                        
                    seen_proxies.add(proxy_str)
                    
                    # Check cache first
                    if proxy_str in self.proxy_cache and len(valid_proxies) < num_proxies:
                        valid_proxies.append(self.proxy_cache[proxy_str])
                        self.logger.info(f"Using cached proxy: {proxy_str}")
                        continue
                    
                    # Validate and get proxy details
                    proxy_details = self.validator.get_proxy_details(proxy_data=proxy_data)
                    if proxy_details:
                        valid_proxies.append(proxy_details)
                        self.proxy_cache[proxy_str] = proxy_details
                        self.logger.info(f"Found valid proxy: {proxy_str}")
                        
                        if len(valid_proxies) >= num_proxies:
                            break
                
                attempts += 1
            
            except Exception as e:
                self.logger.error(f"Error during proxy rotation: {e}")
                attempts += 1
                continue

        if not valid_proxies:
            raise ProxyFinderError(
                f"Failed to find {num_proxies} valid proxies after {attempts} attempts"
            )

        # Sort proxies by speed (response time)
        valid_proxies.sort(key=lambda x: x.get('speed', float('inf')))
        
        return valid_proxies[:num_proxies]
