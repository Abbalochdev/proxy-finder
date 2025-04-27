class ProxyFinderError(Exception):
    """Base exception for Proxy Finder errors."""
    pass

# For backward compatibility
ProxyRotatorError = ProxyFinderError

class ProxyFetchError(ProxyFinderError):
    """Raised when proxy fetching fails."""
    pass

class ProxyValidationError(ProxyFinderError):
    """Raised when proxy validation fails."""
    pass
