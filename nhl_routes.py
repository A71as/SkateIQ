from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from datetime import datetime
from nhl_html import get_html_template

def setup_routes(app, analyzer):
    """Setup all API routes"""
    
    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Home page showing today's NHL games"""
        return get_html_template()
    
    @app.get("/api/todays-games")
    async def get_todays_games():
        """Get today's NHL games schedule"""
        from nhl_daily_predictions import NHLDataFetcher
        try:
            fetcher = NHLDataFetcher()
            games = fetcher.get_todays_games()
            return {
                "success": True,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "games": games,
                "count": len(games)
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch today's games: {str(e)}"
            )
    
    @app.post("/api/analyze")
    async def analyze_matchup(request: dict):
        """Analyze matchup and generate AI prediction"""
        
        if not analyzer:
            raise HTTPException(
                status_code=500,
                detail="Analyzer not initialized. Please configure OPENAI_API_KEY."
            )
        
        try:
            home_team = request.get("home_team", "")
            away_team = request.get("away_team", "")
            game_date = request.get("game_date")
            
            print(f"\n🔍 Analyzing: {home_team} vs {away_team}")
            result = analyzer.analyze_matchup(
                home_team=home_team,
                away_team=away_team,
                game_date=game_date
            )
            print(f"✅ Analysis complete!")
            print(f"📤 Response keys: {result.keys()}")
            if 'error' in result:
                print(f"❌ ERROR in response: {result['error']}")
            print(f"📤 home_team: {result.get('home_team')}")
            print(f"📤 away_team: {result.get('away_team')}")
            if 'analysis' in result:
                print(f"📝 Analysis text: {result['analysis'][:200]}...")
            return result
        except Exception as e:
            print(f"❌ Error during analysis: {str(e)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Analysis failed: {str(e)}"
            )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        from nhl_daily_predictions import client
        return {
            "status": "healthy",
            "service": "NHL Daily Predictions",
            "openai_configured": client is not None,
            "timestamp": datetime.now().isoformat()
        }
