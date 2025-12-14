"""
Input Validation and Sanitization Utilities
Data validation, sanitization, and parsing helpers
"""
from datetime import datetime, date, timedelta
from typing import Optional, List
from pydantic import BaseModel, validator, Field
import re
import logging

logger = logging.getLogger(__name__)


class DateValidator:
    """Date validation utilities"""
    
    @staticmethod
    def validate_date_string(date_str: str) -> bool:
        """Validate date string format (YYYY-MM-DD)"""
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False
    
    @staticmethod
    def parse_date(date_str: str) -> Optional[date]:
        """Parse date string to date object"""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            logger.warning(f"Invalid date format: {date_str}")
            return None
    
    @staticmethod
    def is_future_date(date_str: str, max_days_ahead: int = 7) -> bool:
        """Check if date is in valid future range"""
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            today = date.today()
            max_date = today + timedelta(days=max_days_ahead)
            
            return today <= target_date <= max_date
        except ValueError:
            return False
    
    @staticmethod
    def format_date(d: date) -> str:
        """Format date object to string"""
        return d.strftime("%Y-%m-%d")


class TeamValidator:
    """NHL team name validation"""
    
    VALID_TEAMS = {
        "Anaheim Ducks", "Boston Bruins", "Buffalo Sabres", "Calgary Flames",
        "Carolina Hurricanes", "Chicago Blackhawks", "Colorado Avalanche",
        "Columbus Blue Jackets", "Dallas Stars", "Detroit Red Wings",
        "Edmonton Oilers", "Florida Panthers", "Los Angeles Kings",
        "Minnesota Wild", "Montreal Canadiens", "Nashville Predators",
        "New Jersey Devils", "New York Islanders", "New York Rangers",
        "Ottawa Senators", "Philadelphia Flyers", "Pittsburgh Penguins",
        "San Jose Sharks", "Seattle Kraken", "St. Louis Blues",
        "Tampa Bay Lightning", "Toronto Maple Leafs", "Vancouver Canucks",
        "Vegas Golden Knights", "Washington Capitals", "Winnipeg Jets",
        "Utah Hockey Club", "Arizona Coyotes"
    }
    
    TEAM_ABBREVIATIONS = {
        "ANA": "Anaheim Ducks", "BOS": "Boston Bruins", "BUF": "Buffalo Sabres",
        "CGY": "Calgary Flames", "CAR": "Carolina Hurricanes", "CHI": "Chicago Blackhawks",
        "COL": "Colorado Avalanche", "CBJ": "Columbus Blue Jackets", "DAL": "Dallas Stars",
        "DET": "Detroit Red Wings", "EDM": "Edmonton Oilers", "FLA": "Florida Panthers",
        "LAK": "Los Angeles Kings", "MIN": "Minnesota Wild", "MTL": "Montreal Canadiens",
        "NSH": "Nashville Predators", "NJD": "New Jersey Devils", "NYI": "New York Islanders",
        "NYR": "New York Rangers", "OTT": "Ottawa Senators", "PHI": "Philadelphia Flyers",
        "PIT": "Pittsburgh Penguins", "SJS": "San Jose Sharks", "SEA": "Seattle Kraken",
        "STL": "St. Louis Blues", "TBL": "Tampa Bay Lightning", "TOR": "Toronto Maple Leafs",
        "VAN": "Vancouver Canucks", "VGK": "Vegas Golden Knights", "WSH": "Washington Capitals",
        "WPG": "Winnipeg Jets", "UTA": "Utah Hockey Club", "ARI": "Arizona Coyotes"
    }
    
    @classmethod
    def is_valid_team(cls, team_name: str) -> bool:
        """Check if team name is valid"""
        return team_name in cls.VALID_TEAMS
    
    @classmethod
    def normalize_team_name(cls, team_input: str) -> Optional[str]:
        """
        Normalize team name from various formats
        
        Args:
            team_input: Team name or abbreviation
        
        Returns:
            Full team name or None if invalid
        """
        # Direct match
        if team_input in cls.VALID_TEAMS:
            return team_input
        
        # Abbreviation match
        if team_input.upper() in cls.TEAM_ABBREVIATIONS:
            return cls.TEAM_ABBREVIATIONS[team_input.upper()]
        
        # Fuzzy match (case-insensitive partial match)
        team_input_lower = team_input.lower()
        for valid_team in cls.VALID_TEAMS:
            if team_input_lower in valid_team.lower():
                return valid_team
        
        logger.warning(f"Could not normalize team name: {team_input}")
        return None


class StringSanitizer:
    """String sanitization utilities"""
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 500) -> str:
        """
        Sanitize user input
        
        Args:
            text: Input text
            max_length: Maximum allowed length
        
        Returns:
            Sanitized text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = " ".join(text.split())
        
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length]
        
        # Remove control characters
        text = "".join(char for char in text if ord(char) >= 32 or char in "\n\t")
        
        return text.strip()
    
    @staticmethod
    def sanitize_sql_like(text: str) -> str:
        """Escape special characters for SQL LIKE queries"""
        return text.replace("%", "\\%").replace("_", "\\_")


# Pydantic models for API request validation

class GameAnalysisRequest(BaseModel):
    """Request model for game analysis"""
    home_team: str = Field(..., min_length=1, max_length=100)
    away_team: str = Field(..., min_length=1, max_length=100)
    game_date: Optional[str] = Field(None, regex=r"^\d{4}-\d{2}-\d{2}$")
    
    @validator("home_team", "away_team")
    def validate_team_names(cls, v):
        """Validate and normalize team names"""
        normalized = TeamValidator.normalize_team_name(v)
        if not normalized:
            raise ValueError(f"Invalid team name: {v}")
        return normalized
    
    @validator("game_date")
    def validate_date(cls, v):
        """Validate game date"""
        if v and not DateValidator.validate_date_string(v):
            raise ValueError("Invalid date format. Use YYYY-MM-DD")
        return v


class UserRegistrationRequest(BaseModel):
    """Request model for user registration"""
    username: str = Field(..., min_length=3, max_length=50, regex=r"^[a-zA-Z0-9_-]+$")
    email: str = Field(..., regex=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    password: str = Field(..., min_length=8, max_length=128)
    
    @validator("username")
    def validate_username(cls, v):
        """Validate username"""
        if v.lower() in ["admin", "root", "system", "anonymous"]:
            raise ValueError("Username not allowed")
        return v
    
    @validator("password")
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        
        # Check for at least one letter and one number
        has_letter = any(c.isalpha() for c in v)
        has_number = any(c.isdigit() for c in v)
        
        if not (has_letter and has_number):
            raise ValueError("Password must contain at least one letter and one number")
        
        return v


class PredictionUpdateRequest(BaseModel):
    """Request model for updating prediction results"""
    prediction_id: int = Field(..., gt=0)
    actual_home_score: int = Field(..., ge=0, le=20)
    actual_away_score: int = Field(..., ge=0, le=20)
    
    @validator("actual_home_score", "actual_away_score")
    def validate_scores(cls, v):
        """Validate score values"""
        if v < 0:
            raise ValueError("Scores cannot be negative")
        if v > 20:
            raise ValueError("Score seems unrealistic (max 20)")
        return v


class DateRangeRequest(BaseModel):
    """Request model for date range queries"""
    start_date: str = Field(..., regex=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., regex=r"^\d{4}-\d{2}-\d{2}$")
    
    @validator("start_date", "end_date")
    def validate_dates(cls, v):
        """Validate date format"""
        if not DateValidator.validate_date_string(v):
            raise ValueError("Invalid date format. Use YYYY-MM-DD")
        return v
    
    @validator("end_date")
    def validate_date_range(cls, v, values):
        """Validate date range is logical"""
        if "start_date" in values:
            start = datetime.strptime(values["start_date"], "%Y-%m-%d")
            end = datetime.strptime(v, "%Y-%m-%d")
            
            if end < start:
                raise ValueError("end_date must be after start_date")
            
            if (end - start).days > 365:
                raise ValueError("Date range cannot exceed 365 days")
        
        return v
