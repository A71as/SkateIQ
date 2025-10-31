"""
Automated NHL Game Result Scraper
Fetches completed game results and updates prediction accuracy
"""
import asyncio
import schedule
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from database import get_db, Prediction, update_accuracy_stats
from sqlalchemy.orm import Session
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NHLResultScraper:
    """Scrapes NHL game results and updates prediction accuracy"""
    
    def __init__(self):
        self.base_url = "https://api-web.nhle.com/v1"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SkateIQ-ResultScraper/1.0'
        })
    
    def get_completed_games(self, date: str) -> List[Dict]:
        """Fetch completed games for a specific date"""
        try:
            url = f"{self.base_url}/score/{date}"
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            completed_games = []
            for game in data.get("games", []):
                # Only process completed games
                game_state = game.get("gameState", "")
                if game_state in ["OFF", "FINAL"]:  # Game finished
                    home_team = game.get("homeTeam", {})
                    away_team = game.get("awayTeam", {})
                    
                    home_score = home_team.get("score", 0)
                    away_score = away_team.get("score", 0)
                    
                    # Determine winner
                    if home_score > away_score:
                        winner = "home"
                    elif away_score > home_score:
                        winner = "away"
                    else:
                        winner = "tie"  # Rare in NHL but possible in regulation
                    
                    completed_games.append({
                        "home_team": home_team.get("name", {}).get("default", ""),
                        "away_team": away_team.get("name", {}).get("default", ""),
                        "home_score": home_score,
                        "away_score": away_score,
                        "winner": winner,
                        "game_id": str(game.get("id", "")),
                        "game_date": date,
                        "game_state": game_state
                    })
            
            logger.info(f"Found {len(completed_games)} completed games for {date}")
            return completed_games
            
        except Exception as e:
            logger.error(f"Error fetching games for {date}: {e}")
            return []
    
    def update_predictions_with_results(self, games: List[Dict]) -> Dict[str, int]:
        """Update predictions in database with actual results"""
        db = next(get_db())
        stats = {"updated": 0, "not_found": 0, "errors": 0}
        
        try:
            for game in games:
                try:
                    # Find matching prediction (game_date is stored as string)
                    prediction = db.query(Prediction).filter(
                        Prediction.home_team == game["home_team"],
                        Prediction.away_team == game["away_team"],
                        Prediction.game_date == game["game_date"]
                    ).first()
                    
                    if prediction:
                        # Update with actual results
                        prediction.actual_winner = game["winner"]
                        prediction.actual_home_score = game["home_score"]
                        prediction.actual_away_score = game["away_score"]
                        
                        # Calculate if prediction was correct
                        prediction.is_correct = (prediction.predicted_winner == game["winner"])
                        
                        stats["updated"] += 1
                        logger.info(f"Updated: {game['away_team']} @ {game['home_team']} - "
                                  f"Predicted: {prediction.predicted_winner}, "
                                  f"Actual: {game['winner']}, "
                                  f"Correct: {prediction.is_correct}")
                    else:
                        stats["not_found"] += 1
                        logger.warning(f"No prediction found for: {game['away_team']} @ {game['home_team']} on {game['game_date']}")
                
                except Exception as e:
                    stats["errors"] += 1
                    logger.error(f"Error updating game {game.get('home_team', 'Unknown')}: {e}")
            
            # Commit all updates
            db.commit()
            
            # Recalculate accuracy stats
            if stats["updated"] > 0:
                logger.info("Recalculating accuracy statistics...")
                update_accuracy_stats(db)
                logger.info("Accuracy stats updated")
            
            return stats
            
        except Exception as e:
            db.rollback()
            logger.error(f"Database error during update: {e}")
            stats["errors"] += len(games)
            return stats
        finally:
            db.close()
    
    def scrape_recent_games(self, days_back: int = 3) -> Dict[str, int]:
        """Scrape game results for the last N days"""
        total_stats = {"updated": 0, "not_found": 0, "errors": 0}
        
        logger.info(f"Starting scrape for last {days_back} days...")
        
        for i in range(days_back):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            logger.info(f"Scraping games for {date}...")
            
            games = self.get_completed_games(date)
            if games:
                stats = self.update_predictions_with_results(games)
                
                # Aggregate stats
                for key in total_stats:
                    total_stats[key] += stats[key]
                
                logger.info(f"  {date}: {stats['updated']} updated, {stats['not_found']} not found, {stats['errors']} errors")
            else:
                logger.info(f"  {date}: No completed games found")
            
            # Small delay between requests
            time.sleep(1)
        
        logger.info(f"Scrape complete! Total: {total_stats['updated']} updated, "
                   f"{total_stats['not_found']} not found, {total_stats['errors']} errors")
        
        return total_stats
    
    def get_unresolved_predictions(self, days_back: int = 7) -> List[Dict]:
        """Get predictions that haven't been updated with results yet"""
        db = next(get_db())
        
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            today = datetime.now().strftime('%Y-%m-%d')
            
            unresolved = db.query(Prediction).filter(
                Prediction.game_date >= cutoff_date,
                Prediction.game_date <= today,
                Prediction.actual_winner.is_(None)
            ).all()
            
            result = []
            for pred in unresolved:
                result.append({
                    "id": pred.id,
                    "home_team": pred.home_team,
                    "away_team": pred.away_team,
                    "game_date": pred.game_date,  # Already a string in YYYY-MM-DD format
                    "predicted_winner": pred.predicted_winner,
                    "home_prob": pred.home_prob,
                    "away_prob": pred.away_prob
                })
            
            logger.info(f"Found {len(result)} unresolved predictions")
            return result
            
        except Exception as e:
            logger.error(f"Error getting unresolved predictions: {e}")
            return []
        finally:
            db.close()


# Scheduler functions
def daily_scrape_job():
    """Job to run daily game result scraping"""
    logger.info("🕐 Starting scheduled daily scrape...")
    scraper = NHLResultScraper()
    
    # Scrape last 2 days (yesterday and day before)
    # This ensures we catch any delayed game results
    stats = scraper.scrape_recent_games(days_back=2)
    
    logger.info(f"✅ Daily scrape completed: {stats}")

def weekly_cleanup_job():
    """Job to run weekly cleanup and comprehensive check"""
    logger.info("🕐 Starting scheduled weekly cleanup...")
    scraper = NHLResultScraper()
    
    # Check last 7 days for any missed results
    stats = scraper.scrape_recent_games(days_back=7)
    
    # Log unresolved predictions
    unresolved = scraper.get_unresolved_predictions(days_back=14)
    if unresolved:
        logger.warning(f"Found {len(unresolved)} unresolved predictions:")
        for pred in unresolved[:5]:  # Log first 5
            logger.warning(f"  {pred['away_team']} @ {pred['home_team']} on {pred['game_date']}")
    
    logger.info(f"✅ Weekly cleanup completed: {stats}")

def run_scheduler():
    """Run the scheduler - call this to start automated scraping"""
    logger.info("🤖 Starting NHL Result Scraper Scheduler")
    
    # Schedule daily scraping at 2 AM (after most games finish)
    schedule.every().day.at("02:00").do(daily_scrape_job)
    
    # Schedule weekly comprehensive check on Mondays at 3 AM
    schedule.every().monday.at("03:00").do(weekly_cleanup_job)
    
    logger.info("📅 Scheduled jobs:")
    logger.info("  - Daily scrape: Every day at 2:00 AM")
    logger.info("  - Weekly cleanup: Every Monday at 3:00 AM")
    
    # Run scheduler loop
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

# Manual execution functions
async def manual_scrape(days_back: int = 1):
    """Manually trigger a scrape (useful for testing)"""
    logger.info(f"🔧 Manual scrape requested for last {days_back} days")
    scraper = NHLResultScraper()
    return scraper.scrape_recent_games(days_back=days_back)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "scrape":
            # Manual scrape
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 1
            scraper = NHLResultScraper()
            result = scraper.scrape_recent_games(days_back=days)
            print(f"Scrape completed: {result}")
        elif sys.argv[1] == "unresolved":
            # Show unresolved predictions
            scraper = NHLResultScraper()
            unresolved = scraper.get_unresolved_predictions()
            print(f"Found {len(unresolved)} unresolved predictions:")
            for pred in unresolved:
                print(f"  {pred['away_team']} @ {pred['home_team']} on {pred['game_date']}")
        elif sys.argv[1] == "schedule":
            # Run scheduler
            run_scheduler()
        else:
            print("Usage: python game_result_scraper.py [scrape|unresolved|schedule] [days]")
    else:
        print("NHL Game Result Scraper")
        print("Usage:")
        print("  python game_result_scraper.py scrape [days]    - Manual scrape")
        print("  python game_result_scraper.py unresolved       - Show unresolved predictions")
        print("  python game_result_scraper.py schedule         - Run scheduler")