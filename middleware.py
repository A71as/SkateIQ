"""
Rate Limiting Middleware
Token bucket algorithm for API request throttling
"""
import time
from typing import Dict, Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from collections import defaultdict
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket for rate limiting"""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens
        
        Args:
            tokens: Number of tokens to consume
        
        Returns:
            True if tokens were consumed, False if insufficient
        """
        with self.lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def _refill(self):
        """Refill tokens based on time elapsed"""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def get_tokens(self) -> float:
        """Get current token count"""
        with self.lock:
            self._refill()
            return self.tokens


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using token bucket algorithm"""
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_size: int = 10,
        identifier_func: Callable = None
    ):
        """
        Args:
            app: FastAPI application
            requests_per_minute: Sustained request rate
            burst_size: Maximum burst capacity
            identifier_func: Function to extract identifier from request (default: IP)
        """
        super().__init__(app)
        self.buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(
                capacity=burst_size,
                refill_rate=requests_per_minute / 60.0
            )
        )
        self.identifier_func = identifier_func or self._default_identifier
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
        logger.info(f"Rate limiting enabled: {requests_per_minute} req/min, burst: {burst_size}")
    
    def _default_identifier(self, request: Request) -> str:
        """Extract client IP as identifier"""
        # Check for forwarded IP (proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Check for real IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to client host
        return request.client.host if request.client else "unknown"
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting"""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/api/health"]:
            return await call_next(request)
        
        # Get identifier
        identifier = self.identifier_func(request)
        
        # Get or create bucket for this identifier
        bucket = self.buckets[identifier]
        
        # Try to consume token
        if not bucket.consume():
            logger.warning(f"Rate limit exceeded for {identifier}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "message": "Rate limit exceeded. Please try again later.",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Periodic cleanup of old buckets
        if time.time() - self.last_cleanup > self.cleanup_interval:
            self._cleanup_old_buckets()
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(bucket.capacity)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket.get_tokens()))
        
        return response
    
    def _cleanup_old_buckets(self):
        """Remove buckets with full tokens (inactive clients)"""
        to_remove = []
        for identifier, bucket in self.buckets.items():
            if bucket.get_tokens() >= bucket.capacity * 0.95:
                to_remove.append(identifier)
        
        for identifier in to_remove:
            del self.buckets[identifier]
        
        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} inactive rate limit buckets")
        
        self.last_cleanup = time.time()


class IPRateLimiter:
    """Simple per-IP rate limiter (alternative implementation)"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = defaultdict(list)
        self.lock = Lock()
    
    def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed
        
        Args:
            identifier: Client identifier (usually IP)
        
        Returns:
            True if request is allowed, False if rate limited
        """
        with self.lock:
            now = time.time()
            window_start = now - self.window_seconds
            
            # Get requests for this identifier
            requests = self.requests[identifier]
            
            # Remove old requests outside window
            requests[:] = [req_time for req_time in requests if req_time > window_start]
            
            # Check if under limit
            if len(requests) < self.max_requests:
                requests.append(now)
                return True
            
            return False
    
    def get_remaining(self, identifier: str) -> int:
        """Get remaining requests for identifier"""
        with self.lock:
            now = time.time()
            window_start = now - self.window_seconds
            
            requests = self.requests[identifier]
            requests[:] = [req_time for req_time in requests if req_time > window_start]
            
            return max(0, self.max_requests - len(requests))
