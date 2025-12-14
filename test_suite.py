"""
Comprehensive Unit Tests for SkateIQ
Tests for validators, caching, API utilities, and core logic
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta, date

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from validators import (
    DateValidator,
    TeamValidator,
    StringSanitizer,
    GameAnalysisRequest,
    UserRegistrationRequest
)
from caching import LRUCache, PredictionCache, CacheEntry
from api_utils import RetryConfig, retry_with_backoff
from exceptions import ValidationException
import time


class TestDateValidator:
    """Tests for DateValidator"""
    
    def test_validate_date_string_valid(self):
        """Test valid date string"""
        assert DateValidator.validate_date_string("2025-12-14")
        assert DateValidator.validate_date_string("2024-01-01")
    
    def test_validate_date_string_invalid(self):
        """Test invalid date strings"""
        assert not DateValidator.validate_date_string("2025-13-14")  # Invalid month
        assert not DateValidator.validate_date_string("14-12-2025")  # Wrong format
        assert not DateValidator.validate_date_string("invalid")
    
    def test_parse_date_valid(self):
        """Test parsing valid date"""
        result = DateValidator.parse_date("2025-12-14")
        assert result == date(2025, 12, 14)
    
    def test_parse_date_invalid(self):
        """Test parsing invalid date returns None"""
        result = DateValidator.parse_date("invalid")
        assert result is None
    
    def test_is_future_date(self):
        """Test future date validation"""
        today = date.today()
        tomorrow = (today + timedelta(days=1)).strftime("%Y-%m-%d")
        week_from_now = (today + timedelta(days=7)).strftime("%Y-%m-%d")
        too_far = (today + timedelta(days=10)).strftime("%Y-%m-%d")
        
        assert DateValidator.is_future_date(tomorrow, max_days_ahead=7)
        assert DateValidator.is_future_date(week_from_now, max_days_ahead=7)
        assert not DateValidator.is_future_date(too_far, max_days_ahead=7)
    
    def test_format_date(self):
        """Test date formatting"""
        d = date(2025, 12, 14)
        assert DateValidator.format_date(d) == "2025-12-14"


class TestTeamValidator:
    """Tests for TeamValidator"""
    
    def test_is_valid_team(self):
        """Test team name validation"""
        assert TeamValidator.is_valid_team("Boston Bruins")
        assert TeamValidator.is_valid_team("Vegas Golden Knights")
        assert not TeamValidator.is_valid_team("Invalid Team")
    
    def test_normalize_team_name_full_name(self):
        """Test normalization with full name"""
        assert TeamValidator.normalize_team_name("Boston Bruins") == "Boston Bruins"
    
    def test_normalize_team_name_abbreviation(self):
        """Test normalization with abbreviation"""
        assert TeamValidator.normalize_team_name("BOS") == "Boston Bruins"
        assert TeamValidator.normalize_team_name("VGK") == "Vegas Golden Knights"
    
    def test_normalize_team_name_partial(self):
        """Test normalization with partial match"""
        assert TeamValidator.normalize_team_name("Bruins") == "Boston Bruins"
        assert TeamValidator.normalize_team_name("golden") == "Vegas Golden Knights"
    
    def test_normalize_team_name_invalid(self):
        """Test normalization with invalid team returns None"""
        assert TeamValidator.normalize_team_name("Invalid Team") is None


class TestStringSanitizer:
    """Tests for StringSanitizer"""
    
    def test_sanitize_input_normal(self):
        """Test normal string sanitization"""
        result = StringSanitizer.sanitize_input("Hello World")
        assert result == "Hello World"
    
    def test_sanitize_input_excessive_whitespace(self):
        """Test removing excessive whitespace"""
        result = StringSanitizer.sanitize_input("Hello    World   ")
        assert result == "Hello World"
    
    def test_sanitize_input_max_length(self):
        """Test max length truncation"""
        long_string = "a" * 1000
        result = StringSanitizer.sanitize_input(long_string, max_length=100)
        assert len(result) == 100
    
    def test_sanitize_input_empty(self):
        """Test empty string"""
        result = StringSanitizer.sanitize_input("")
        assert result == ""
    
    def test_sanitize_sql_like(self):
        """Test SQL LIKE escape"""
        result = StringSanitizer.sanitize_sql_like("test%value_here")
        assert result == "test\\%value\\_here"


class TestGameAnalysisRequest:
    """Tests for GameAnalysisRequest pydantic model"""
    
    def test_valid_request(self):
        """Test valid game analysis request"""
        request = GameAnalysisRequest(
            home_team="Boston Bruins",
            away_team="New York Rangers",
            game_date="2025-12-14"
        )
        assert request.home_team == "Boston Bruins"
        assert request.away_team == "New York Rangers"
        assert request.game_date == "2025-12-14"
    
    def test_normalize_team_names(self):
        """Test automatic team name normalization"""
        request = GameAnalysisRequest(
            home_team="BOS",
            away_team="Rangers",
            game_date="2025-12-14"
        )
        assert request.home_team == "Boston Bruins"
        assert request.away_team == "New York Rangers"
    
    def test_invalid_team_name(self):
        """Test invalid team name raises error"""
        with pytest.raises(Exception):
            GameAnalysisRequest(
                home_team="Invalid Team",
                away_team="Boston Bruins",
                game_date="2025-12-14"
            )
    
    def test_invalid_date_format(self):
        """Test invalid date format raises error"""
        with pytest.raises(Exception):
            GameAnalysisRequest(
                home_team="Boston Bruins",
                away_team="New York Rangers",
                game_date="14-12-2025"
            )


class TestUserRegistrationRequest:
    """Tests for UserRegistrationRequest"""
    
    def test_valid_registration(self):
        """Test valid user registration"""
        request = UserRegistrationRequest(
            username="testuser123",
            email="test@example.com",
            password="SecurePass123"
        )
        assert request.username == "testuser123"
    
    def test_username_too_short(self):
        """Test username too short raises error"""
        with pytest.raises(Exception):
            UserRegistrationRequest(
                username="ab",
                email="test@example.com",
                password="SecurePass123"
            )
    
    def test_invalid_username_characters(self):
        """Test invalid username characters"""
        with pytest.raises(Exception):
            UserRegistrationRequest(
                username="test user!",
                email="test@example.com",
                password="SecurePass123"
            )
    
    def test_reserved_username(self):
        """Test reserved usernames are rejected"""
        with pytest.raises(Exception):
            UserRegistrationRequest(
                username="admin",
                email="test@example.com",
                password="SecurePass123"
            )
    
    def test_weak_password(self):
        """Test weak password raises error"""
        with pytest.raises(Exception):
            UserRegistrationRequest(
                username="testuser",
                email="test@example.com",
                password="weak"
            )
    
    def test_password_no_number(self):
        """Test password without number raises error"""
        with pytest.raises(Exception):
            UserRegistrationRequest(
                username="testuser",
                email="test@example.com",
                password="OnlyLetters"
            )


class TestLRUCache:
    """Tests for LRUCache"""
    
    def test_cache_set_and_get(self):
        """Test basic set and get operations"""
        cache = LRUCache(max_size=10, default_ttl=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
    
    def test_cache_miss(self):
        """Test cache miss returns None"""
        cache = LRUCache(max_size=10, default_ttl=60)
        assert cache.get("nonexistent") is None
    
    def test_cache_expiration(self):
        """Test cache entry expiration"""
        cache = LRUCache(max_size=10, default_ttl=1)
        cache.set("key1", "value1", ttl=1)
        assert cache.get("key1") == "value1"
        
        time.sleep(2)
        assert cache.get("key1") is None
    
    def test_cache_eviction(self):
        """Test LRU eviction when at capacity"""
        cache = LRUCache(max_size=3, default_ttl=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # This should evict key1 (least recently used)
        cache.set("key4", "value4")
        
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
    
    def test_cache_stats(self):
        """Test cache statistics"""
        cache = LRUCache(max_size=10, default_ttl=60)
        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        
        stats = cache.get_stats()
        assert stats["size"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0
    
    def test_cache_clear(self):
        """Test cache clear"""
        cache = LRUCache(max_size=10, default_ttl=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get_stats()["size"] == 0


class TestPredictionCache:
    """Tests for PredictionCache"""
    
    def test_prediction_cache(self):
        """Test prediction-specific caching"""
        cache = PredictionCache(ttl_hours=1, max_size=100)
        
        prediction = {
            "home_prob": 55,
            "away_prob": 45,
            "confidence": 7
        }
        
        cache.set_prediction("Boston Bruins", "New York Rangers", "2025-12-14", prediction)
        
        result = cache.get_prediction("Boston Bruins", "New York Rangers", "2025-12-14")
        assert result == prediction
    
    def test_prediction_invalidation(self):
        """Test prediction invalidation"""
        cache = PredictionCache(ttl_hours=1, max_size=100)
        
        prediction = {"home_prob": 55, "away_prob": 45}
        cache.set_prediction("Boston Bruins", "New York Rangers", "2025-12-14", prediction)
        
        assert cache.invalidate_prediction("Boston Bruins", "New York Rangers", "2025-12-14")
        assert cache.get_prediction("Boston Bruins", "New York Rangers", "2025-12-14") is None


class TestRetryMechanism:
    """Tests for retry mechanism"""
    
    def test_retry_success_on_first_attempt(self):
        """Test successful execution on first try"""
        attempt_count = []
        
        @retry_with_backoff(RetryConfig(max_retries=3))
        def successful_func():
            attempt_count.append(1)
            return "success"
        
        result = successful_func()
        assert result == "success"
        assert len(attempt_count) == 1
    
    def test_retry_success_after_failures(self):
        """Test success after initial failures"""
        attempt_count = []
        
        @retry_with_backoff(RetryConfig(max_retries=3, backoff_factor=0.1))
        def flaky_func():
            attempt_count.append(1)
            if len(attempt_count) < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = flaky_func()
        assert result == "success"
        assert len(attempt_count) == 3
    
    def test_retry_max_attempts_exceeded(self):
        """Test failure after max retries"""
        @retry_with_backoff(RetryConfig(max_retries=2, backoff_factor=0.1))
        def failing_func():
            raise Exception("Persistent failure")
        
        with pytest.raises(Exception) as exc_info:
            failing_func()
        
        assert "Persistent failure" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
