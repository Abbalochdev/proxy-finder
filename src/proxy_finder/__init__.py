from .core.rotation import ProxyManager
from .exceptions import ProxyRotatorError as ProxyFinderError

__version__ = '1.2.0'

__all__ = ['ProxyManager', 'ProxyFinderError']

# For backward compatibility
ProxyRotatorError = ProxyFinderError
