#!/usr/bin/env python3
"""
Quick test script to debug the accuracy endpoint
"""
import sys
import traceback
from database import init_db, get_db, get_or_create_overall_stats, update_accuracy_stats

def test_accuracy_endpoint():
    try:
        print("Testing accuracy endpoint logic...")
        
        # Initialize database
        init_db()
        print("✓ Database initialized")
        
        # Get database session
        db = next(get_db())
        print("✓ Database session created")
        
        # Get stats
        stats = get_or_create_overall_stats(db)
        print(f"✓ Stats retrieved: {stats.total_predictions} total, {stats.accuracy_percentage}% accuracy")
        
        # Update stats
        update_accuracy_stats(db)
        print("✓ Stats updated")
        
        # Refresh and check
        db.refresh(stats)
        print(f"✓ Final stats: {stats.total_predictions} total, {stats.accuracy_percentage}% accuracy")
        
        # Test response format
        response = {
            "success": True,
            "total_predictions": stats.total_predictions,
            "correct_predictions": stats.correct_predictions,
            "accuracy_percentage": round(stats.accuracy_percentage, 1),
            "last_7_days_accuracy": round(stats.last_7_days_accuracy or 0, 1),
            "last_30_days_accuracy": round(stats.last_30_days_accuracy or 0, 1),
        }
        print(f"✓ Response format: {response}")
        
        db.close()
        print("✓ Test completed successfully!")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_accuracy_endpoint()
    sys.exit(0 if success else 1)