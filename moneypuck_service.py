"""
MoneyPuck.com Data Service
Fetches NHL team and game data from MoneyPuck's comprehensive analytics platform
Data source: https://moneypuck.com/data.htm
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MoneyPuckService:
    """Service for fetching NHL data from MoneyPuck.com"""
    
    def __init__(self):
        self.base_url = "https://moneypuck.com/moneypuck/playerData"
        self.season = self._get_current_season()
        self.team_data_cache = None
        self.cache_timestamp = None
        self.cache_ttl = timedelta(hours=1)
        
        # Team abbreviation mapping (MoneyPuck uses different abbreviations)
        self.team_mapping = {
            "Anaheim Ducks": "ANA",
            "Boston Bruins": "BOS",
            "Buffalo Sabres": "BUF",
            "Calgary Flames": "CGY",
            "Carolina Hurricanes": "CAR",
            "Chicago Blackhawks": "CHI",
            "Colorado Avalanche": "COL",
            "Columbus Blue Jackets": "CBJ",
            "Dallas Stars": "DAL",
            "Detroit Red Wings": "DET",
            "Edmonton Oilers": "EDM",
            "Florida Panthers": "FLA",
            "Los Angeles Kings": "L.A",
            "Minnesota Wild": "MIN",
            "Montreal Canadiens": "MTL",
            "Montréal Canadiens": "MTL",
            "Nashville Predators": "NSH",
            "New Jersey Devils": "N.J",
            "New York Islanders": "NYI",
            "New York Rangers": "NYR",
            "Ottawa Senators": "OTT",
            "Philadelphia Flyers": "PHI",
            "Pittsburgh Penguins": "PIT",
            "San Jose Sharks": "S.J",
            "Seattle Kraken": "SEA",
            "St. Louis Blues": "STL",
            "Tampa Bay Lightning": "T.B",
            "Toronto Maple Leafs": "TOR",
            "Vancouver Canucks": "VAN",
            "Vegas Golden Knights": "VGK",
            "Washington Capitals": "WSH",
            "Winnipeg Jets": "WPG",
            "Utah Hockey Club": "UTA",
            "Arizona Coyotes": "ARI"
        }
        
        # Reverse mapping for display names
        self.abbrev_to_name = {v: k for k, v in self.team_mapping.items()}
    
    def _get_current_season(self) -> str:
        """Determine current NHL season year (e.g., '2025' for 2025-26 season)"""
        now = datetime.now()
        # NHL season runs from October to June
        # MoneyPuck uses the starting year only (2025 for 2025-26 season)
        # If we're in months Jan-June, the season started last year
        # If we're in months Jul-Dec, the season starts this year
        if now.month <= 6:
            return str(now.year - 1)
        else:
            return str(now.year)
    
    def _get_team_data(self, force_refresh=False) -> pd.DataFrame:
        """Fetch team-level data from MoneyPuck with caching"""
        # Check cache
        if (not force_refresh and 
            self.team_data_cache is not None and 
            self.cache_timestamp and 
            datetime.now() - self.cache_timestamp < self.cache_ttl):
            logger.info("Using cached MoneyPuck team data")
            return self.team_data_cache
        
        # Try current season first, then fall back to previous seasons
        current_year = int(self.season)
        seasons_to_try = [
            str(current_year),      # Current season (2025 for 2025-26)
            str(current_year - 1),  # Previous season (2024 for 2024-25)
            str(current_year - 2)   # Two seasons ago (2023 for 2023-24)
        ]
        
        for season in seasons_to_try:
            try:
                url = f"https://moneypuck.com/moneypuck/playerData/seasonSummary/{season}/regular/teams.csv"
                logger.info(f"Fetching MoneyPuck team data from: {url}")
                
                df = pd.read_csv(url)
                self.team_data_cache = df
                self.cache_timestamp = datetime.now()
                
                logger.info(f"Successfully loaded {len(df)} rows from {season}-{int(season)+1} season")
                return df
                
            except Exception as e:
                logger.warning(f"Could not fetch {season} data: {e}")
                continue
        
        # If all attempts fail, return empty DataFrame
        logger.error("Failed to fetch MoneyPuck data from all season attempts")
        return pd.DataFrame(columns=['team', 'name'])
    
    def get_team_stats(self, team_name: str) -> Dict:
        """Get comprehensive team statistics from MoneyPuck"""
        try:
            df = self._get_team_data()
            
            # Get team abbreviation
            team_abbrev = self.team_mapping.get(team_name, team_name[:3].upper())
            
            # Find team in data - filter for 'all' situations for overall stats
            team_row = df[(df['team'] == team_abbrev) & (df['situation'] == 'all')]
            
            if team_row.empty:
                logger.warning(f"Team {team_name} ({team_abbrev}) not found in MoneyPuck data")
                return self._get_default_stats(team_name, team_abbrev)
            
            row = team_row.iloc[0]
            
            # Calculate shooting % and save %
            shots_for = float(row.get('shotsOnGoalFor', 1))
            shots_against = float(row.get('shotsOnGoalAgainst', 1))
            goals_for = float(row.get('goalsFor', 0))
            goals_against = float(row.get('goalsAgainst', 0))
            
            shooting_pct = (goals_for / shots_for * 100) if shots_for > 0 else 0
            save_pct = ((shots_against - goals_against) / shots_against * 100) if shots_against > 0 else 90
            
            # Get special teams stats from 5on4 and 4on5 situations
            pp_row = df[(df['team'] == team_abbrev) & (df['situation'] == '5on4')]
            pk_row = df[(df['team'] == team_abbrev) & (df['situation'] == '4on5')]
            
            pp_pct = 0.0
            pk_pct = 0.0
            
            if not pp_row.empty:
                pp_goals = float(pp_row.iloc[0].get('goalsFor', 0))
                pp_shots = float(pp_row.iloc[0].get('shotsOnGoalFor', 1))
                pp_pct = (pp_goals / pp_shots * 100) if pp_shots > 0 else 0
            
            if not pk_row.empty:
                pk_goals_against = float(pk_row.iloc[0].get('goalsAgainst', 0))
                pk_shots_against = float(pk_row.iloc[0].get('shotsOnGoalAgainst', 1))
                pk_pct = ((pk_shots_against - pk_goals_against) / pk_shots_against * 100) if pk_shots_against > 0 else 75
            
            # Extract key statistics
            games_played = int(row.get('games_played', 30))
            
            # Estimate wins/losses from goal differential (rough approximation)
            goal_diff = goals_for - goals_against
            estimated_points_pct = 0.5 + (goal_diff / games_played / 6.0) if games_played > 0 else 0.5
            estimated_points_pct = max(0.2, min(0.8, estimated_points_pct))
            
            estimated_wins = int(games_played * estimated_points_pct * 0.6)
            estimated_losses = int(games_played * (1 - estimated_points_pct) * 0.7)
            estimated_ot_losses = games_played - estimated_wins - estimated_losses
            
            stats = {
                'team_name': team_name,
                'abbrev': team_abbrev,
                
                # Record and standings (estimated from performance)
                'wins': estimated_wins,
                'losses': estimated_losses,
                'ot_losses': max(0, estimated_ot_losses),
                'games_played': games_played,
                'points': estimated_wins * 2 + estimated_ot_losses,
                
                # Actual scoring data from MoneyPuck
                'goals_for': int(goals_for),
                'goals_against': int(goals_against),
                'goal_diff': int(goal_diff),
                
                # Advanced metrics from MoneyPuck - THE GOLDMINE
                'xGoalsFor': round(float(row.get('xGoalsFor', 0)), 2),
                'xGoalsAgainst': round(float(row.get('xGoalsAgainst', 0)), 2),
                'corsiFor': round(float(row.get('corsiPercentage', 0.5)) * 100, 1),
                'fenwickFor': round(float(row.get('fenwickPercentage', 0.5)) * 100, 1),
                'shooting_pct': round(shooting_pct, 1),
                'save_pct': round(save_pct, 1),
                
                # Power play and penalty kill
                'pp_pct': round(pp_pct, 1),
                'pk_pct': round(pk_pct, 1),
                
                # Additional advanced metrics
                'high_danger_shots_for': int(row.get('highDangerShotsFor', 0)),
                'high_danger_shots_against': int(row.get('highDangerShotsAgainst', 0)),
                'high_danger_goals_for': int(row.get('highDangerGoalsFor', 0)),
                
                # Point percentage
                'point_pct': round(estimated_points_pct, 3),
                
                # Recent form (estimated)
                'streak': 'W' if goal_diff > 5 else 'L' if goal_diff < -5 else 'OT',
                'last_10': f"{min(estimated_wins, 10)}-{min(estimated_losses, 10)}-{min(estimated_ot_losses, 10)}",
                
                # Home/road splits (estimated 50/50)
                'home_record': f"{estimated_wins//2}-{estimated_losses//2}-{estimated_ot_losses//2}",
                'road_record': f"{estimated_wins - estimated_wins//2}-{estimated_losses - estimated_losses//2}-{estimated_ot_losses - estimated_ot_losses//2}",
                
                # MoneyPuck specific
                'rating': None,  # Not in this dataset
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting team stats for {team_name}: {e}")
            import traceback
            traceback.print_exc()
            return self._get_default_stats(team_name, self.team_mapping.get(team_name, "UNK"))
    
    def _get_default_stats(self, team_name: str, abbrev: str) -> Dict:
        """Return default stats when data is unavailable"""
        return {
            'team_name': team_name,
            'abbrev': abbrev,
            'wins': 0,
            'losses': 0,
            'ot_losses': 0,
            'games_played': 0,
            'points': 0,
            'goals_for': 0,
            'goals_against': 0,
            'goal_diff': 0,
            'xGoalsFor': 0.0,
            'xGoalsAgainst': 0.0,
            'corsiFor': 50.0,
            'fenwickFor': 50.0,
            'shooting_pct': 0.0,
            'save_pct': 90.0,
            'pp_pct': 0.0,
            'pk_pct': 0.0,
            'point_pct': 0.5,
            'streak': 'N/A',
            'last_10': '0-0-0',
            'home_record': '0-0-0',
            'road_record': '0-0-0',
            'rating': 0.0
        }
    
    def get_team_roster(self, team_name: str) -> Dict:
        """Get team roster information (simplified for now)"""
        team_abbrev = self.team_mapping.get(team_name, team_name[:3].upper())
        
        return {
            'top_forwards': [f"{team_name} Forward 1", f"{team_name} Forward 2", f"{team_name} Forward 3"],
            'top_defense': [f"{team_name} Defenseman 1", f"{team_name} Defenseman 2"],
            'goalies': [f"{team_name} Goalie 1", f"{team_name} Goalie 2"]
        }
    
    def get_todays_games(self) -> List[Dict]:
        """
        Get today's NHL games schedule
        Note: MoneyPuck doesn't provide schedule API, so we'll integrate with NHL API for schedules
        but use MoneyPuck for team stats
        """
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Use NHL API for schedule (MoneyPuck doesn't have this)
            nhl_api_url = f"https://api-web.nhle.com/v1/score/{today}"
            response = requests.get(nhl_api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            games = []
            game_list = data.get("games", [])
            
            for game in game_list:
                away_team = game.get("awayTeam", {})
                home_team = game.get("homeTeam", {})
                
                game_data = {
                    "home_team": home_team.get("name", {}).get("default", ""),
                    "away_team": away_team.get("name", {}).get("default", ""),
                    "time": game.get("startTimeUTC", "TBD"),
                    "date": today,
                    "event_id": str(game.get("id", "")),
                    "game_state": game.get("gameState", ""),
                    "home_abbrev": home_team.get("abbrev", ""),
                    "away_abbrev": away_team.get("abbrev", "")
                }
                
                games.append(game_data)
            
            logger.info(f"Found {len(games)} games for {today}")
            return games
            
        except Exception as e:
            logger.error(f"Error fetching today's games: {e}")
            return []
    
    def get_games_by_date(self, date: str) -> List[Dict]:
        """Get games for a specific date"""
        try:
            nhl_api_url = f"https://api-web.nhle.com/v1/score/{date}"
            response = requests.get(nhl_api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            games = []
            game_list = data.get("games", [])
            
            for game in game_list:
                away_team = game.get("awayTeam", {})
                home_team = game.get("homeTeam", {})
                
                game_data = {
                    "home_team": home_team.get("name", {}).get("default", ""),
                    "away_team": away_team.get("name", {}).get("default", ""),
                    "home_score": home_team.get("score", 0),
                    "away_score": away_team.get("score", 0),
                    "time": game.get("startTimeUTC", "TBD"),
                    "date": date,
                    "event_id": str(game.get("id", "")),
                    "game_state": game.get("gameState", ""),
                    "period": game.get("period", 0),
                    "home_abbrev": home_team.get("abbrev", ""),
                    "away_abbrev": away_team.get("abbrev", "")
                }
                
                games.append(game_data)
            
            return games
            
        except Exception as e:
            logger.error(f"Error fetching games for {date}: {e}")
            return []


if __name__ == "__main__":
    # Test the MoneyPuck service
    print("🏒 Testing MoneyPuck Data Service")
    print("=" * 50)
    
    service = MoneyPuckService()
    
    # Test team stats
    print("\n📊 Testing Team Stats:")
    teams_to_test = ["Toronto Maple Leafs", "Boston Bruins", "Colorado Avalanche"]
    
    for team in teams_to_test:
        stats = service.get_team_stats(team)
        print(f"\n{team}:")
        print(f"  Record: {stats['wins']}-{stats['losses']}-{stats['ot_losses']}")
        print(f"  Goals: {stats['goals_for']} GF, {stats['goals_against']} GA")
        print(f"  xGoals: {stats['xGoalsFor']} xGF, {stats['xGoalsAgainst']} xGA")
        print(f"  Corsi: {stats['corsiFor']}%, Shooting%: {stats['shooting_pct']}%")
    
    # Test today's games
    print("\n📅 Testing Today's Games:")
    games = service.get_todays_games()
    print(f"Found {len(games)} games today")
    for game in games[:3]:
        print(f"  {game['away_team']} @ {game['home_team']}")
    
    print("\n✅ MoneyPuck service test complete!")
