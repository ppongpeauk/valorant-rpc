class RiotRefuseError(Exception):
    """Raised when the client refuses to connect to the local server"""
    pass
class RiotTimeoutError(Exception):
    """Raised when the client refuses to connect to the local server"""
    pass
class RiotAuthError(Exception):
    """Usually raised when the client is not authenticated"""
    pass
class RiotPresenceError(Exception):
    """Usually raised when the client cannot access their own presence"""
    pass
