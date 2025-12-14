"""
Custom Exception Classes
Structured error handling for SkateIQ application
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class SkateIQException(Exception):
    """Base exception for SkateIQ application"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DatabaseException(SkateIQException):
    """Database-related errors"""
    pass


class APIException(SkateIQException):
    """External API-related errors"""
    pass


class NHLAPIException(APIException):
    """NHL API specific errors"""
    pass


class MoneyPuckException(APIException):
    """MoneyPuck API specific errors"""
    pass


class OpenAIException(APIException):
    """OpenAI API specific errors"""
    pass


class AuthenticationException(SkateIQException):
    """Authentication-related errors"""
    pass


class ValidationException(SkateIQException):
    """Data validation errors"""
    pass


class CacheException(SkateIQException):
    """Caching-related errors"""
    pass


class RateLimitException(SkateIQException):
    """Rate limiting errors"""
    pass


# HTTP Exception helpers
def not_found_exception(resource: str, identifier: Any) -> HTTPException:
    """Generate 404 Not Found exception"""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource} with identifier '{identifier}' not found"
    )


def unauthorized_exception(detail: str = "Not authenticated") -> HTTPException:
    """Generate 401 Unauthorized exception"""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def forbidden_exception(detail: str = "Insufficient permissions") -> HTTPException:
    """Generate 403 Forbidden exception"""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail
    )


def bad_request_exception(detail: str) -> HTTPException:
    """Generate 400 Bad Request exception"""
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail
    )


def conflict_exception(detail: str) -> HTTPException:
    """Generate 409 Conflict exception"""
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail
    )


def service_unavailable_exception(service: str, detail: Optional[str] = None) -> HTTPException:
    """Generate 503 Service Unavailable exception"""
    message = f"{service} is currently unavailable"
    if detail:
        message += f": {detail}"
    
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=message
    )


def internal_server_error(detail: str = "Internal server error") -> HTTPException:
    """Generate 500 Internal Server Error exception"""
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=detail
    )


def rate_limit_exceeded_exception(retry_after: Optional[int] = None) -> HTTPException:
    """Generate 429 Too Many Requests exception"""
    headers = {}
    if retry_after:
        headers["Retry-After"] = str(retry_after)
    
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Rate limit exceeded. Please try again later.",
        headers=headers
    )
