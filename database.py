"""
Database configuration and models for SkateIQ
PostgreSQL + SQLAlchemy ORM
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Database URL - supports both PostgreSQL and SQLite for development
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./skateiq.db"  # Fallback to SQLite for local development
)

# Handle Render.com PostgreSQL URL format (postgres:// -> postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    pool_pre_ping=True,  # Verify connections before using
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


# ============================================================================
# DATABASE MODELS
# ============================================================================

class User(Base):
    """User account model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    predictions = relationship("Prediction", back_populates="user")
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"


class Prediction(Base):
    """NHL game prediction model"""
    __tablename__ = "predictions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # NULL for anonymous predictions
    
    # Game details
    home_team = Column(String(100), nullable=False, index=True)
    away_team = Column(String(100), nullable=False, index=True)
    game_date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    game_id = Column(String(50), nullable=True, index=True)
    
    # Prediction data
    home_prob = Column(Integer, nullable=False)  # 0-100
    away_prob = Column(Integer, nullable=False)  # 0-100
    confidence = Column(Integer, nullable=False)  # 1-10
    predicted_winner = Column(String(10), nullable=False)  # "home" or "away"
    
    # Analysis text
    analysis_text = Column(Text, nullable=True)
    
    # Actual result (filled after game)
    actual_winner = Column(String(10), nullable=True)  # "home" or "away"
    actual_home_score = Column(Integer, nullable=True)
    actual_away_score = Column(Integer, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="predictions")
    
    def __repr__(self):
        return f"<Prediction({self.away_team} @ {self.home_team} on {self.game_date})>"


class AccuracyStats(Base):
    """Aggregated accuracy statistics (for quick lookups)"""
    __tablename__ = "accuracy_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # NULL for overall stats
    
    # Stats
    total_predictions = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    accuracy_percentage = Column(Float, default=0.0)
    
    # Time-based stats
    last_7_days_total = Column(Integer, default=0)
    last_7_days_correct = Column(Integer, default=0)
    last_30_days_total = Column(Integer, default=0)
    last_30_days_correct = Column(Integer, default=0)
    
    # Metadata
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<AccuracyStats(user_id={self.user_id}, accuracy={self.accuracy_percentage}%)>"


# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


def get_db():
    """Dependency for getting database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_or_create_overall_stats(db):
    """Get or create overall accuracy stats (user_id = NULL)"""
    stats = db.query(AccuracyStats).filter(AccuracyStats.user_id == None).first()
    if not stats:
        stats = AccuracyStats(user_id=None)
        db.add(stats)
        db.commit()
        db.refresh(stats)
    return stats


def update_accuracy_stats(db, user_id=None):
    """Recalculate and update accuracy statistics"""
    from datetime import timedelta
    from sqlalchemy import func
    
    # Get all predictions for this user (or all if user_id is None)
    query = db.query(Prediction).filter(Prediction.is_correct.isnot(None))
    if user_id:
        query = query.filter(Prediction.user_id == user_id)
    else:
        query = query.filter(Prediction.user_id == None)
    
    # Overall stats
    total = query.count()
    correct = query.filter(Prediction.is_correct == True).count()
    accuracy = round((correct / total * 100) if total > 0 else 0, 1)
    
    # Last 7 days
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    last_7_query = query.filter(Prediction.created_at >= seven_days_ago)
    last_7_total = last_7_query.count()
    last_7_correct = last_7_query.filter(Prediction.is_correct == True).count()
    
    # Last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    last_30_query = query.filter(Prediction.created_at >= thirty_days_ago)
    last_30_total = last_30_query.count()
    last_30_correct = last_30_query.filter(Prediction.is_correct == True).count()
    
    # Update or create stats
    stats = db.query(AccuracyStats).filter(AccuracyStats.user_id == user_id).first()
    if not stats:
        stats = AccuracyStats(user_id=user_id)
        db.add(stats)
    
    stats.total_predictions = total
    stats.correct_predictions = correct
    stats.accuracy_percentage = accuracy
    stats.last_7_days_total = last_7_total
    stats.last_7_days_correct = last_7_correct
    stats.last_30_days_total = last_30_total
    stats.last_30_days_correct = last_30_correct
    stats.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(stats)
    return stats


if __name__ == "__main__":
    print("🗄️  Initializing SkateIQ Database...")
    init_db()
    print("✅ Done!")
