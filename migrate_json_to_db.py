"""
Migration utility to move predictions from JSON to PostgreSQL
One-time script to preserve existing data
"""
import json
from datetime import datetime
from pathlib import Path
from database import init_db, get_db, Prediction, update_accuracy_stats
from sqlalchemy.orm import Session

def migrate_predictions():
    """Migrate predictions from data/predictions.json to PostgreSQL"""
    # Initialize database
    print("Initializing database...")
    init_db()
    print("✓ Database tables created")
    
    # Load JSON data
    json_path = Path("data/predictions.json")
    if not json_path.exists():
        print(f"✗ No JSON file found at {json_path}")
        print("Creating empty predictions.json...")
        json_path.parent.mkdir(exist_ok=True)
        with open(json_path, 'w') as f:
            json.dump({"predictions": {}}, f)
        print("✓ Empty predictions file created")
        return
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    predictions_data = data.get('predictions', [])
    total = len(predictions_data)
    
    if total == 0:
        print("✓ No existing predictions to migrate")
        return
    
    print(f"Found {total} predictions to migrate...")
    
    # Get database session
    db = next(get_db())
    
    try:
        migrated = 0
        skipped = 0
        
        for pred in predictions_data:
            # Parse game_date - handle both ISO and simple date formats
            game_date_str = pred['game_date']
            if 'T' in game_date_str:
                game_date = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
            else:
                game_date = datetime.strptime(game_date_str, '%Y-%m-%d')
            
            # Check if prediction already exists
            existing = db.query(Prediction).filter(
                Prediction.home_team == pred['home_team'],
                Prediction.away_team == pred['away_team'],
                Prediction.game_date == game_date
            ).first()
            
            if existing:
                skipped += 1
                continue
            
            # Create prediction record
            prediction = Prediction(
                home_team=pred['home_team'],
                away_team=pred['away_team'],
                game_date=game_date,
                home_prob=float(pred.get('home_prob', pred.get('home_win_probability', 50))),
                away_prob=float(pred.get('away_prob', pred.get('away_win_probability', 50))),
                confidence=str(pred.get('confidence', 'medium')),
                predicted_winner=pred['predicted_winner'],
                actual_winner=pred.get('actual_winner'),
                is_correct=pred.get('is_correct'),
                analysis_text=pred.get('analysis', pred.get('analysis_text', '')),
                user_id=None  # Migrated predictions have no user
            )
            
            db.add(prediction)
            migrated += 1
            
            if migrated % 10 == 0:
                print(f"  Migrated {migrated}/{total}...")
        
        db.commit()
        print(f"✓ Migration complete: {migrated} migrated, {skipped} skipped")
        
        # Update accuracy stats
        print("Updating accuracy statistics...")
        update_accuracy_stats(db)
        print("✓ Accuracy stats updated")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_predictions()
