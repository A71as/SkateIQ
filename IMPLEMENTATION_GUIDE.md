# SkateIQ Implementation Guide

## Quick Start with New Features

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/skateiq

# API Keys
OPENAI_API_KEY=sk-your-key-here

# Security
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here

# Environment
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO

# Performance
CACHE_TTL_HOURS=6
RATE_LIMIT_REQUESTS=100
API_REQUEST_TIMEOUT=15
```

### 3. Run Tests

```bash
# Run all tests
pytest test_suite.py -v

# Run with coverage report
pytest test_suite.py --cov=. --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### 4. Run Application

```bash
python nhl_daily_predictions.py
```

Application will start on: http://localhost:8001

## New Features Usage

### Configuration Management

```python
from config import settings

# Access settings anywhere in your code
api_key = settings.OPENAI_API_KEY
is_prod = settings.is_production
cache_ttl = settings.CACHE_TTL_HOURS

# Settings are type-safe and validated at startup
```

### Logging

```python
from logging_config import setup_logging, get_logger

# Setup once at application startup
setup_logging(
    log_level=settings.LOG_LEVEL,
    log_file="logs/skateiq.log"
)

# Use in any module
logger = get_logger(__name__)

logger.info("Processing request")
logger.warning("Cache miss")
logger.error("API failed", exc_info=True)
```

### Input Validation

```python
from validators import GameAnalysisRequest

# Automatic validation and normalization
request = GameAnalysisRequest(
    home_team="BOS",  # Normalized to "Boston Bruins"
    away_team="Rangers",  # Normalized to "New York Rangers"
    game_date="2025-12-14"
)

# Invalid input raises clear validation errors
try:
    bad_request = GameAnalysisRequest(
        home_team="Invalid Team",
        away_team="Boston Bruins"
    )
except ValidationError as e:
    print(e.errors())
```

### Caching

```python
from caching import PredictionCache

# Initialize cache
cache = PredictionCache(ttl_hours=6)

# Check cache first
prediction = cache.get_prediction("Bruins", "Rangers", "2025-12-14")

if not prediction:
    # Generate prediction
    prediction = generate_prediction(...)
    
    # Store in cache
    cache.set_prediction("Bruins", "Rangers", "2025-12-14", prediction)

# Get cache stats
stats = cache.get_stats()
print(f"Cache hit rate: {stats['hit_rate']}%")
```

### API Retry Logic

```python
from api_utils import retry_with_backoff, RetryConfig, APIClient

# Use decorator for automatic retries
@retry_with_backoff(RetryConfig(max_retries=3))
def fetch_data(url):
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.json()

# Or use APIClient with built-in retries
client = APIClient("https://api-web.nhle.com/v1", timeout=15)
games = client.get("/schedule/2025-12-14")
```

### Exception Handling

```python
from exceptions import (
    NHLAPIException,
    OpenAIException,
    not_found_exception,
    service_unavailable_exception
)

# Raise specific exceptions
try:
    data = fetch_nhl_data()
except requests.RequestException as e:
    raise NHLAPIException("Failed to fetch NHL data", {"error": str(e)})

# Use HTTP exception helpers
if not prediction:
    raise not_found_exception("Prediction", prediction_id)

if openai_down:
    raise service_unavailable_exception("OpenAI", "Rate limit exceeded")
```

### Rate Limiting

Rate limiting is automatically applied via middleware. Configure in settings:

```python
# config.py or .env
RATE_LIMIT_ENABLED=True
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60
```

Responses include rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
```

When exceeded, returns 429 with:
```json
{
  "error": "Too Many Requests",
  "message": "Rate limit exceeded. Please try again later.",
  "retry_after": 60
}
```

## Integration with Existing Code

### Update nhl_daily_predictions.py

```python
# Add at top of file
from config import settings
from logging_config import setup_logging, get_logger
from caching import PredictionCache
from middleware import RateLimitMiddleware
from validators import GameAnalysisRequest
from exceptions import NHLAPIException

# Setup logging
setup_logging(
    log_level=settings.LOG_LEVEL,
    log_file="logs/skateiq.log"
)

logger = get_logger(__name__)

# Initialize cache
prediction_cache = PredictionCache(
    ttl_hours=settings.CACHE_TTL_HOURS
)

# Add rate limiting middleware
if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.RATE_LIMIT_REQUESTS
    )

# Update analyze endpoint to use cache
@app.post("/api/analyze")
async def analyze_game(request: GameAnalysisRequest, db: Session = Depends(get_db)):
    # Try cache first
    cached = prediction_cache.get_prediction(
        request.home_team,
        request.away_team,
        request.game_date
    )
    
    if cached:
        logger.info(f"Cache hit for {request.away_team} @ {request.home_team}")
        return cached
    
    # Generate prediction
    logger.info(f"Generating prediction for {request.away_team} @ {request.home_team}")
    
    try:
        prediction = await analyzer.analyze(
            request.home_team,
            request.away_team,
            request.game_date
        )
        
        # Cache result
        prediction_cache.set_prediction(
            request.home_team,
            request.away_team,
            request.game_date,
            prediction
        )
        
        return prediction
    
    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        raise NHLAPIException("Prediction generation failed", {"error": str(e)})
```

### Update database.py

```python
from config import settings

# Use settings for database configuration
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_pre_ping=True,
    echo=settings.DEBUG
)
```

### Update auth.py

```python
from config import settings

# Use settings for auth configuration
SECRET_KEY = settings.SECRET_KEY
JWT_SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
```

## Testing

### Run Specific Test Classes

```bash
# Test validators
pytest test_suite.py::TestDateValidator -v

# Test caching
pytest test_suite.py::TestLRUCache -v

# Test API utils
pytest test_suite.py::TestRetryMechanism -v
```

### Add Your Own Tests

```python
# test_custom.py
import pytest
from validators import TeamValidator

def test_custom_team_validation():
    assert TeamValidator.is_valid_team("Boston Bruins")
    assert TeamValidator.normalize_team_name("BOS") == "Boston Bruins"

def test_custom_logic():
    # Your test here
    pass
```

## Monitoring

### Check Cache Performance

```python
from caching import prediction_cache

stats = prediction_cache.get_stats()
print(f"""
Cache Statistics:
- Size: {stats['size']}/{stats['max_size']}
- Hits: {stats['hits']}
- Misses: {stats['misses']}
- Hit Rate: {stats['hit_rate']}%
- Total Requests: {stats['total_requests']}
""")
```

### View Logs

```bash
# Tail application logs
tail -f logs/skateiq.log

# View error logs only
grep ERROR logs/skateiq.log

# View last 100 lines
tail -100 logs/skateiq.log
```

### Health Check

```bash
# Check application health
curl http://localhost:8001/health

# Check with Docker
docker exec skateiq-app curl http://localhost:8001/health
```

## Deployment

### Build Docker Image

```bash
docker build -t aoa29/skateiq:v3.0.0 .
docker push aoa29/skateiq:v3.0.0
```

### Update Production

```bash
# On server
cd ~/projects/skateiq
git pull
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

### Environment Variables for Production

```env
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=INFO
CACHE_TTL_HOURS=6
RATE_LIMIT_REQUESTS=100
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
```

## Troubleshooting

### High Memory Usage

```python
# Reduce cache size
CACHE_MAX_SIZE=500  # Default: 1000

# Reduce cache TTL
CACHE_TTL_HOURS=3  # Default: 6
```

### Slow API Responses

```python
# Increase cache TTL
CACHE_TTL_HOURS=12

# Increase database pool
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
```

### Rate Limit Issues

```python
# Increase rate limit
RATE_LIMIT_REQUESTS=200
RATE_LIMIT_WINDOW_SECONDS=60

# Or disable for specific IPs
# (implement IP whitelist in middleware.py)
```

## Best Practices

1. **Always use type hints** for better IDE support
2. **Use logging** instead of print statements
3. **Validate all user input** with Pydantic models
4. **Cache expensive operations** (API calls, AI predictions)
5. **Handle exceptions** with specific exception types
6. **Write tests** for new features
7. **Document functions** with docstrings
8. **Use configuration** from settings, not hardcoded values

## Support

For issues or questions:
1. Check `CODE_AUDIT_REPORT.md` for detailed documentation
2. Review `test_suite.py` for usage examples
3. Check logs in `logs/skateiq.log`
4. Open an issue on GitHub

