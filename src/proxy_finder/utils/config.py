from typing import Dict, Any
import json
import os

class ConfigManager:
    """Manages configuration for the proxy finder."""
    
    def __init__(self, config_path: str = None):
        """
        Initialize ConfigManager with optional config file.
        
        Args:
            config_path (str, optional): Path to configuration file.
        """
        self.default_config = {
            'max_retries': 3,
            'timeout': 10.0,
            'proxy_sources': [
                'https://free-proxy-list.net/',
                'https://www.proxy-list.download/api/v1/get?type=http'
            ]
        }
        
        self.config_path = config_path or os.path.expanduser('~/.proxy_finder.json')
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file or return default.
        
        Returns:
            Dict[str, Any]: Configuration dictionary.
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                    return {**self.default_config, **user_config}
            return self.default_config
        except (json.JSONDecodeError, PermissionError):
            return self.default_config

    def save_config(self, new_config: Dict[str, Any] = None):
        """
        Save configuration to file.
        
        Args:
            new_config (Dict[str, Any], optional): New configuration to save.
        """
        config_to_save = new_config or self.config
        
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config_to_save, f, indent=4)
        except PermissionError:
            print(f"Warning: Unable to save config to {self.config_path}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key (str): Configuration key.
            default (Any, optional): Default value if key not found.
        
        Returns:
            Any: Configuration value.
        """
        return self.config.get(key, default)
