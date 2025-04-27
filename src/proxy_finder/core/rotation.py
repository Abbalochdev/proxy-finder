from typing import List, Dict, Any, Optional
import logging

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

        while len(valid_proxies) < num_proxies and attempts < max_attempts * num_proxies:
            try:
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
                    all_proxies = self.fetcher.fetch_proxies()
                
                # Filter out already seen proxies
                new_proxies = [p for p in all_proxies if p.get('proxy') not in seen_proxies]
                if not new_proxies:
                    self.logger.warning("No new proxies available")
                    break

                for proxy_data in new_proxies:
                    proxy_str = proxy_data.get('proxy')
                    seen_proxies.add(proxy_str)
                    
                    # Validate and get proxy details
                    proxy_details = self.validator.get_proxy_details(proxy_data=proxy_data)
                    if proxy_details:
                        valid_proxies.append(proxy_details)
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
