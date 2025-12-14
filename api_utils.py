"""
API Request Utilities
Retry logic, timeouts, and error handling for external APIs
"""
import asyncio
import aiohttp
import requests
from typing import Optional, Dict, Any, Callable
from functools import wraps
import time
import logging

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry logic"""
    
    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        max_backoff: float = 60.0,
        timeout: int = 15,
        retry_on_status: list = None
    ):
        """
        Args:
            max_retries: Maximum number of retry attempts
            backoff_factor: Exponential backoff multiplier
            max_backoff: Maximum backoff time in seconds
            timeout: Request timeout in seconds
            retry_on_status: HTTP status codes to retry on
        """
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.max_backoff = max_backoff
        self.timeout = timeout
        self.retry_on_status = retry_on_status or [408, 429, 500, 502, 503, 504]


def retry_with_backoff(config: RetryConfig = None):
    """
    Decorator for retrying functions with exponential backoff
    
    Args:
        config: RetryConfig instance (uses defaults if None)
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    
                    # Check if result is a Response object with error status
                    if hasattr(result, 'status_code') and result.status_code in config.retry_on_status:
                        raise Exception(f"HTTP {result.status_code}")
                    
                    return result
                
                except Exception as e:
                    last_exception = e
                    
                    if attempt < config.max_retries:
                        # Calculate backoff time
                        backoff = min(
                            config.backoff_factor ** attempt,
                            config.max_backoff
                        )
                        
                        logger.warning(
                            f"Attempt {attempt + 1}/{config.max_retries + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {backoff:.2f}s..."
                        )
                        
                        time.sleep(backoff)
                    else:
                        logger.error(f"All {config.max_retries + 1} attempts failed for {func.__name__}: {e}")
            
            raise last_exception
        
        return wrapper
    return decorator


async def retry_async_with_backoff(config: RetryConfig = None):
    """
    Async decorator for retrying async functions with exponential backoff
    
    Args:
        config: RetryConfig instance (uses defaults if None)
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    result = await func(*args, **kwargs)
                    return result
                
                except Exception as e:
                    last_exception = e
                    
                    if attempt < config.max_retries:
                        backoff = min(
                            config.backoff_factor ** attempt,
                            config.max_backoff
                        )
                        
                        logger.warning(
                            f"Async attempt {attempt + 1}/{config.max_retries + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {backoff:.2f}s..."
                        )
                        
                        await asyncio.sleep(backoff)
                    else:
                        logger.error(f"All {config.max_retries + 1} async attempts failed for {func.__name__}: {e}")
            
            raise last_exception
        
        return wrapper
    return decorator


class APIClient:
    """HTTP client with built-in retry and timeout logic"""
    
    def __init__(self, base_url: str, timeout: int = 15, max_retries: int = 3):
        """
        Args:
            base_url: Base URL for API requests
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "SkateIQ/3.0.0",
            "Accept": "application/json"
        })
    
    @retry_with_backoff(RetryConfig(max_retries=3, timeout=15))
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        GET request with retry logic
        
        Args:
            endpoint: API endpoint (will be appended to base_url)
            params: Query parameters
        
        Returns:
            JSON response as dictionary
        
        Raises:
            requests.RequestException: If request fails after retries
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        logger.debug(f"GET {url} with params {params}")
        
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        
        return response.json()
    
    @retry_with_backoff(RetryConfig(max_retries=3, timeout=15))
    def post(self, endpoint: str, data: Optional[Dict] = None, json: Optional[Dict] = None) -> Dict[str, Any]:
        """
        POST request with retry logic
        
        Args:
            endpoint: API endpoint
            data: Form data
            json: JSON data
        
        Returns:
            JSON response as dictionary
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        logger.debug(f"POST {url}")
        
        response = self.session.post(url, data=data, json=json, timeout=self.timeout)
        response.raise_for_status()
        
        return response.json()
    
    def close(self):
        """Close session"""
        self.session.close()


class AsyncAPIClient:
    """Async HTTP client with retry logic"""
    
    def __init__(self, base_url: str, timeout: int = 15, max_retries: int = 3):
        """
        Args:
            base_url: Base URL for API requests
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
    
    async def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Async GET request with retry logic
        
        Args:
            endpoint: API endpoint
            params: Query parameters
        
        Returns:
            JSON response as dictionary
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            for attempt in range(self.max_retries + 1):
                try:
                    logger.debug(f"Async GET {url} (attempt {attempt + 1})")
                    
                    async with session.get(url, params=params) as response:
                        response.raise_for_status()
                        return await response.json()
                
                except Exception as e:
                    if attempt < self.max_retries:
                        backoff = 2 ** attempt
                        logger.warning(f"Request failed, retrying in {backoff}s: {e}")
                        await asyncio.sleep(backoff)
                    else:
                        logger.error(f"Request failed after {self.max_retries + 1} attempts: {e}")
                        raise
    
    async def post(self, endpoint: str, data: Optional[Dict] = None, json: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Async POST request with retry logic
        
        Args:
            endpoint: API endpoint
            data: Form data
            json: JSON data
        
        Returns:
            JSON response as dictionary
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            for attempt in range(self.max_retries + 1):
                try:
                    logger.debug(f"Async POST {url} (attempt {attempt + 1})")
                    
                    async with session.post(url, data=data, json=json) as response:
                        response.raise_for_status()
                        return await response.json()
                
                except Exception as e:
                    if attempt < self.max_retries:
                        backoff = 2 ** attempt
                        logger.warning(f"Request failed, retrying in {backoff}s: {e}")
                        await asyncio.sleep(backoff)
                    else:
                        logger.error(f"Request failed after {self.max_retries + 1} attempts: {e}")
                        raise


def circuit_breaker(failure_threshold: int = 5, timeout: int = 60):
    """
    Circuit breaker pattern for API calls
    
    Args:
        failure_threshold: Number of failures before opening circuit
        timeout: Seconds before attempting to close circuit
    """
    failures = 0
    last_failure_time = None
    is_open = False
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            nonlocal failures, last_failure_time, is_open
            
            # Check if circuit should be closed
            if is_open and last_failure_time:
                if time.time() - last_failure_time >= timeout:
                    logger.info(f"Circuit breaker: Attempting to close circuit for {func.__name__}")
                    is_open = False
                    failures = 0
            
            # If circuit is open, fail fast
            if is_open:
                raise Exception(f"Circuit breaker is OPEN for {func.__name__}. Failing fast.")
            
            try:
                result = func(*args, **kwargs)
                # Success - reset failures
                if failures > 0:
                    logger.info(f"Circuit breaker: Resetting failures for {func.__name__}")
                failures = 0
                return result
            
            except Exception as e:
                failures += 1
                last_failure_time = time.time()
                
                if failures >= failure_threshold:
                    is_open = True
                    logger.error(f"Circuit breaker: OPENED for {func.__name__} after {failures} failures")
                
                raise
        
        return wrapper
    return decorator
