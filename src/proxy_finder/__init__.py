from .core.rotation import ProxyManager
from .exceptions import ProxyRotatorError as ProxyFinderError

__all__ = ['ProxyManager', 'ProxyFinderError']

# For backward compatibility
ProxyRotatorError = ProxyFinderError
