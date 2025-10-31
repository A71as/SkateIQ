"""
Analytics and visualization endpoints for SkateIQ
Provides data for charts and statistical insights
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database import get_db, Prediction, User
from fastapi import Depends, HTTPException
import calendar

def get_accuracy_trends(db: Session, days: int = 30, user_id: Optional[int] = None) -> Dict:
    """Get accuracy trends over time"""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Base query
        query = db.query(Prediction).filter(
            Prediction.game_date >= start_date.strftime('%Y-%m-%d'),
            Prediction.game_date <= end_date.strftime('%Y-%m-%d'),
            Prediction.is_correct.isnot(None)
        )
        
        if user_id:
            query = query.filter(Prediction.user_id == user_id)
        
        # Group by date and calculate daily accuracy
        daily_stats = {}
        predictions = query.all()
        
        for pred in predictions:
            date = pred.game_date
            if date not in daily_stats:
                daily_stats[date] = {"total": 0, "correct": 0}
            
            daily_stats[date]["total"] += 1
            if pred.is_correct:
                daily_stats[date]["correct"] += 1
        
        # Format for chart
        dates = []
        accuracies = []
        totals = []
        
        for date in sorted(daily_stats.keys()):
            stats = daily_stats[date]
            accuracy = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
            
            dates.append(date)
            accuracies.append(round(accuracy, 1))
            totals.append(stats["total"])
        
        return {
            "dates": dates,
            "accuracies": accuracies,
            "prediction_counts": totals,
            "period_days": days
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get accuracy trends: {str(e)}")

def get_confidence_analysis(db: Session, user_id: Optional[int] = None) -> Dict:
    """Analyze accuracy by confidence level"""
    try:
        query = db.query(Prediction).filter(Prediction.is_correct.isnot(None))
        
        if user_id:
            query = query.filter(Prediction.user_id == user_id)
        
        predictions = query.all()
        
        # Group by confidence level
        confidence_stats = {}
        for pred in predictions:
            conf = str(pred.confidence)
            if conf not in confidence_stats:
                confidence_stats[conf] = {"total": 0, "correct": 0}
            
            confidence_stats[conf]["total"] += 1
            if pred.is_correct:
                confidence_stats[conf]["correct"] += 1
        
        # Format for chart
        levels = []
        accuracies = []
        counts = []
        
        for conf in sorted(confidence_stats.keys(), key=lambda x: int(x) if x.isdigit() else 0):
            stats = confidence_stats[conf]
            accuracy = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
            
            levels.append(f"{conf}/10")
            accuracies.append(round(accuracy, 1))
            counts.append(stats["total"])
        
        return {
            "confidence_levels": levels,
            "accuracies": accuracies,
            "prediction_counts": counts
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get confidence analysis: {str(e)}")

def get_team_performance(db: Session, user_id: Optional[int] = None, limit: int = 10) -> Dict:
    """Get accuracy performance by team"""
    try:
        query = db.query(Prediction).filter(Prediction.is_correct.isnot(None))
        
        if user_id:
            query = query.filter(Prediction.user_id == user_id)
        
        predictions = query.all()
        
        # Analyze both home and away performance
        team_stats = {}
        
        for pred in predictions:
            # Home team performance
            home_team = pred.home_team
            if home_team not in team_stats:
                team_stats[home_team] = {"total": 0, "correct": 0, "home_games": 0, "away_games": 0}
            
            team_stats[home_team]["total"] += 1
            team_stats[home_team]["home_games"] += 1
            if pred.is_correct:
                team_stats[home_team]["correct"] += 1
            
            # Away team performance
            away_team = pred.away_team
            if away_team not in team_stats:
                team_stats[away_team] = {"total": 0, "correct": 0, "home_games": 0, "away_games": 0}
            
            team_stats[away_team]["total"] += 1
            team_stats[away_team]["away_games"] += 1
            if pred.is_correct:
                team_stats[away_team]["correct"] += 1
        
        # Calculate accuracy and sort
        team_results = []
        for team, stats in team_stats.items():
            if stats["total"] >= 3:  # Only include teams with 3+ predictions
                accuracy = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
                team_results.append({
                    "team": team,
                    "accuracy": round(accuracy, 1),
                    "total_predictions": stats["total"],
                    "correct_predictions": stats["correct"],
                    "home_games": stats["home_games"],
                    "away_games": stats["away_games"]
                })
        
        # Sort by accuracy (descending) and limit
        team_results.sort(key=lambda x: x["accuracy"], reverse=True)
        
        return {
            "best_teams": team_results[:limit],
            "worst_teams": team_results[-limit:] if len(team_results) > limit else [],
            "total_teams": len(team_results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get team performance: {str(e)}")

def get_prediction_streaks(db: Session, user_id: Optional[int] = None) -> Dict:
    """Get current and longest prediction streaks"""
    try:
        query = db.query(Prediction).filter(Prediction.is_correct.isnot(None))
        
        if user_id:
            query = query.filter(Prediction.user_id == user_id)
        
        # Order by game date and created_at
        predictions = query.order_by(Prediction.game_date, Prediction.created_at).all()
        
        if not predictions:
            return {
                "current_streak": {"type": "none", "count": 0},
                "longest_correct_streak": 0,
                "longest_incorrect_streak": 0,
                "total_predictions": 0
            }
        
        # Calculate streaks
        current_streak = 0
        current_streak_type = None
        longest_correct = 0
        longest_incorrect = 0
        temp_correct = 0
        temp_incorrect = 0
        
        for pred in predictions:
            if pred.is_correct:
                temp_correct += 1
                temp_incorrect = 0
                if current_streak_type != "correct":
                    current_streak = 1
                    current_streak_type = "correct"
                else:
                    current_streak += 1
            else:
                temp_incorrect += 1
                temp_correct = 0
                if current_streak_type != "incorrect":
                    current_streak = 1
                    current_streak_type = "incorrect"
                else:
                    current_streak += 1
            
            longest_correct = max(longest_correct, temp_correct)
            longest_incorrect = max(longest_incorrect, temp_incorrect)
        
        return {
            "current_streak": {
                "type": current_streak_type or "none",
                "count": current_streak
            },
            "longest_correct_streak": longest_correct,
            "longest_incorrect_streak": longest_incorrect,
            "total_predictions": len(predictions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get prediction streaks: {str(e)}")

def get_home_away_analysis(db: Session, user_id: Optional[int] = None) -> Dict:
    """Analyze prediction accuracy for home vs away teams"""
    try:
        query = db.query(Prediction).filter(Prediction.is_correct.isnot(None))
        
        if user_id:
            query = query.filter(Prediction.user_id == user_id)
        
        predictions = query.all()
        
        home_stats = {"total": 0, "correct": 0}
        away_stats = {"total": 0, "correct": 0}
        
        for pred in predictions:
            if pred.predicted_winner == "home":
                home_stats["total"] += 1
                if pred.is_correct:
                    home_stats["correct"] += 1
            elif pred.predicted_winner == "away":
                away_stats["total"] += 1
                if pred.is_correct:
                    away_stats["correct"] += 1
        
        home_accuracy = (home_stats["correct"] / home_stats["total"] * 100) if home_stats["total"] > 0 else 0
        away_accuracy = (away_stats["correct"] / away_stats["total"] * 100) if away_stats["total"] > 0 else 0
        
        return {
            "home_predictions": {
                "accuracy": round(home_accuracy, 1),
                "total": home_stats["total"],
                "correct": home_stats["correct"]
            },
            "away_predictions": {
                "accuracy": round(away_accuracy, 1),
                "total": away_stats["total"],
                "correct": away_stats["correct"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get home/away analysis: {str(e)}")