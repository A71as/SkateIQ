def get_html_template():
    """Returns the HTML template for the daily predictions page"""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>NHL Daily Predictions - AI Powered</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            padding: 20px;
            color: #fff;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        header {
            text-align: center;
            margin-bottom: 40px;
            padding: 30px;
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .subtitle {
            color: #a0aec0;
            font-size: 1.1em;
        }
        .date-header {
            text-align: center;
            font-size: 1.3em;
            margin: 20px 0;
            color: #667eea;
        }
        .loading {
            text-align: center;
            padding: 60px 20px;
            font-size: 1.2em;
            color: #a0aec0;
        }
        .spinner {
            border: 4px solid rgba(255,255,255,0.1);
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .games-grid {
            display: grid;
            gap: 20px;
            margin-top: 30px;
        }
        .game-card {
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 25px;
            border: 1px solid rgba(255,255,255,0.1);
            transition: all 0.3s ease;
        }
        .game-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
            border-color: rgba(102, 126, 234, 0.5);
        }
        .matchup-header {
            display: grid;
            grid-template-columns: 2fr auto 2fr;
            align-items: center;
            gap: 20px;
            margin-bottom: 20px;
            padding-bottom: 20px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .team {
            text-align: center;
        }
        .team-name {
            font-size: 1.4em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .team-location {
            font-size: 0.85em;
            color: #a0aec0;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 5px;
        }
        .vs {
            font-size: 1.2em;
            color: #667eea;
            font-weight: bold;
        }
        .game-time {
            text-align: center;
            color: #a0aec0;
            font-size: 0.95em;
            margin-bottom: 15px;
        }
        .prediction {
            background: rgba(102, 126, 234, 0.1);
            border-radius: 12px;
            padding: 20px;
            margin-top: 15px;
        }
        .win-probabilities {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 15px;
        }
        .probability {
            text-align: center;
            padding: 15px;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
        }
        .probability-label {
            font-size: 0.9em;
            color: #a0aec0;
            margin-bottom: 5px;
        }
        .probability-value {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        .winner {
            background: rgba(102, 234, 134, 0.1);
        }
        .winner .probability-value {
            color: #66ea86;
        }
        .confidence {
            text-align: center;
            margin-top: 10px;
            padding: 10px;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            font-size: 0.95em;
        }
        .analyze-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
            width: 100%;
            margin-top: 10px;
            transition: all 0.3s ease;
        }
        .analyze-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        .analyze-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        .error {
            background: rgba(239, 68, 68, 0.1);
            border: 2px solid rgba(239, 68, 68, 0.3);
            border-radius: 12px;
            padding: 20px;
            color: #fca5a5;
            text-align: center;
        }
        .no-games {
            text-align: center;
            padding: 60px 20px;
            font-size: 1.2em;
            color: #a0aec0;
        }
        .analysis-text {
            margin-top: 15px;
            padding: 15px;
            background: rgba(255,255,255,0.03);
            border-radius: 8px;
            line-height: 1.6;
            font-size: 0.95em;
            color: #e2e8f0;
        }
        .analysis-text h4 {
            margin: 10px 0 6px;
            font-size: 1.05em;
            color: #cbd5e1;
        }
        .analysis-text ul {
            margin: 6px 0 10px 18px;
        }
        footer {
            text-align: center;
            margin-top: 60px;
            padding: 30px 20px;
            background: rgba(255,255,255,0.05);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            border: 1px solid rgba(255,255,255,0.1);
            color: #a0aec0;
        }
        footer p {
            margin: 10px 0;
            font-size: 1em;
        }
        footer a {
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        footer a:hover {
            color: #764ba2;
            text-decoration: underline;
        }
        .github-link {
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏒 SkateIQ</h1>
            <p class="subtitle">AI-Powered NHL Predictions • Daily Matchup Analysis</p>
        </header>

        <div class="date-header" id="dateHeader">📅 Loading today's games...</div>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Fetching today's NHL schedule...</p>
        </div>

        <div class="games-grid" id="gamesGrid"></div>
        
        <footer>
            <p>Created by <strong>Ahmed Alami</strong></p>
            <p>
                <a href="https://github.com/A71as" target="_blank" class="github-link">
                    <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
                    </svg>
                    @A71as
                </a>
            </p>
        </footer>
    </div>

    <script>
        // Team emoji mapping
        const teamEmojis = {
            // Metropolitan Division
            'Carolina Hurricanes': '🌀', 'Hurricanes': '🌀',
            'New Jersey Devils': '😈', 'Devils': '😈',
            'New York Rangers': '🗽', 'Rangers': '🗽',
            'New York Islanders': '🏝️', 'Islanders': '🏝️',
            'Philadelphia Flyers': '🧡', 'Flyers': '🧡',
            'Pittsburgh Penguins': '🐧', 'Penguins': '🐧',
            'Columbus Blue Jackets': '💥', 'Blue Jackets': '💥',
            'Washington Capitals': '🦅', 'Capitals': '🦅',
            
            // Atlantic Division
            'Boston Bruins': '🐻', 'Bruins': '🐻',
            'Florida Panthers': '🐆', 'Panthers': '🐆',
            'Toronto Maple Leafs': '🍁', 'Maple Leafs': '🍁',
            'Tampa Bay Lightning': '⚡', 'Lightning': '⚡',
            'Detroit Red Wings': '🪽', 'Red Wings': '🪽',
            'Buffalo Sabres': '⚔️', 'Sabres': '⚔️',
            'Ottawa Senators': '🏛️', 'Senators': '🏛️',
            'Montreal Canadiens': '⚜️', 'Canadiens': '⚜️',
            
            // Central Division
            'Dallas Stars': '⭐', 'Stars': '⭐',
            'Colorado Avalanche': '🏔️', 'Avalanche': '🏔️',
            'Winnipeg Jets': '✈️', 'Jets': '✈️',
            'Minnesota Wild': '🌲', 'Wild': '🌲',
            'St. Louis Blues': '🎺', 'Blues': '🎺',
            'Nashville Predators': '🎸', 'Predators': '🎸',
            'Arizona Coyotes': '🌵', 'Coyotes': '🌵',
            'Chicago Blackhawks': '🪶', 'Blackhawks': '🪶',
            
            // Pacific Division
            'Vegas Golden Knights': '⚔️', 'Golden Knights': '⚔️',
            'Edmonton Oilers': '🛢️', 'Oilers': '🛢️',
            'Los Angeles Kings': '👑', 'Kings': '👑',
            'Vancouver Canucks': '🐋', 'Canucks': '🐋',
            'Calgary Flames': '🔥', 'Flames': '🔥',
            'Seattle Kraken': '🦑', 'Kraken': '🦑',
            'Anaheim Ducks': '🦆', 'Ducks': '🦆',
            'San Jose Sharks': '🦈', 'Sharks': '🦈',
            
            // Special cases
            'Utah Hockey Club': '🏔️'
        };
        
        function getTeamEmoji(teamName) {
            return teamEmojis[teamName] || '🏒';
        }
        
        function formatGameTime(timeString) {
            if (!timeString || timeString === 'TBD' || timeString === 'Time TBD') {
                return 'Time TBD';
            }
            
            try {
                // Parse UTC time string (format: "2025-10-31T23:00:00Z")
                const date = new Date(timeString);
                
                // Convert to local time with readable format
                const options = {
                    hour: 'numeric',
                    minute: '2-digit',
                    hour12: true,
                    timeZoneName: 'short'
                };
                
                return date.toLocaleTimeString('en-US', options);
            } catch (error) {
                return timeString;
            }
        }
        
        async function loadTodaysGames() {
            try {
                const response = await fetch('/api/todays-games');
                const data = await response.json();
                
                document.getElementById('loading').style.display = 'none';
                
                if (!data.success || data.games.length === 0) {
                    document.getElementById('gamesGrid').innerHTML = `
                        <div class="no-games">
                            <h2>No NHL games scheduled for today</h2>
                            <p style="margin-top: 10px; color: #667eea;">Check back tomorrow for predictions!</p>
                        </div>
                    `;
                    document.getElementById('dateHeader').textContent = 
                        `📅 ${new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}`;
                    return;
                }
                
                document.getElementById('dateHeader').textContent = 
                    `📅 ${new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })} • ${data.games.length} Games`;
                
                const gamesGrid = document.getElementById('gamesGrid');
                gamesGrid.innerHTML = data.games.map((game, index) => `
                    <div class="game-card" id="game-${index}">
                        <div class="matchup-header">
                            <div class="team">
                                <div class="team-name">${getTeamEmoji(game.away_team)} ${game.away_team} ${getTeamEmoji(game.away_team)}</div>
                                <div class="team-location">✈️ Away ✈️</div>
                            </div>
                            <div class="vs">VS</div>
                            <div class="team">
                                <div class="team-name">${getTeamEmoji(game.home_team)} ${game.home_team} ${getTeamEmoji(game.home_team)}</div>
                                <div class="team-location">🏠 Home 🏠</div>
                            </div>
                        </div>
                        <div class="game-time">🕒 ${formatGameTime(game.time)}</div>
                        <button class="analyze-btn" onclick="analyzeGame(${index}, '${game.home_team}', '${game.away_team}')" id="btn-${index}">
                            🤖 Get AI Prediction
                        </button>
                        <div id="prediction-${index}"></div>
                    </div>
                `).join('');
                
            } catch (error) {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('gamesGrid').innerHTML = `
                    <div class="error">
                        <h3>❌ Error Loading Games</h3>
                        <p>${error.message}</p>
                    </div>
                `;
            }
        }

        async function analyzeGame(index, homeTeam, awayTeam) {
            const btn = document.getElementById(`btn-${index}`);
            const predictionDiv = document.getElementById(`prediction-${index}`);
            
            btn.disabled = true;
            btn.textContent = '🧠 AI Analyzing...';
            
            predictionDiv.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    <p>Analyzing matchup... (10-15 seconds)</p>
                </div>
            `;
            
            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        home_team: homeTeam,
                        away_team: awayTeam
                    })
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Analysis failed');
                }
                
                const data = await response.json();
                displayPrediction(index, data);
                
            } catch (error) {
                predictionDiv.innerHTML = `
                    <div class="error">
                        <h4>❌ Prediction Error</h4>
                        <p>${error.message}</p>
                        <p style="margin-top: 10px; font-size: 0.9em;">Check your OpenAI API credits.</p>
                    </div>
                `;
            } finally {
                btn.disabled = false;
                btn.textContent = '🔄 Refresh Prediction';
            }
        }

        function displayPrediction(index, data) {
            const predictionDiv = document.getElementById(`prediction-${index}`);
            const analysis = (data.analysis_text || data.analysis || '');
            
            // Prefer server-parsed fields if available
            let homeProb = Number.isFinite(data.home_prob) ? Number(data.home_prob) : null;
            let awayProb = Number.isFinite(data.away_prob) ? Number(data.away_prob) : null;
            let confidence = Number.isFinite(data.confidence) ? Number(data.confidence) : null;
            
            // Fallback to regex parsing if needed
            if (homeProb === null || awayProb === null) {
                const homeProbMatch = analysis.match(/Home Team:\\s*(\\d+)%/i);
                const awayProbMatch = analysis.match(/Away Team:\\s*(\\d+)%/i);
                if (homeProb === null && homeProbMatch) homeProb = parseInt(homeProbMatch[1]);
                if (awayProb === null && awayProbMatch) awayProb = parseInt(awayProbMatch[1]);
            }
            if (confidence === null) {
                const confidenceMatch = analysis.match(/(\\d+)\\/10/);
                if (confidenceMatch) confidence = parseInt(confidenceMatch[1]);
            }
            
            // Final defaults and clamp
            if (homeProb === null && awayProb === null) { homeProb = 50; awayProb = 50; }
            else if (homeProb === null && awayProb !== null) { homeProb = 100 - awayProb; }
            else if (homeProb !== null && awayProb === null) { awayProb = 100 - homeProb; }
            homeProb = Math.max(0, Math.min(100, Math.round(homeProb)));
            awayProb = Math.max(0, Math.min(100, Math.round(awayProb)));
            const total = homeProb + awayProb;
            if (total !== 100 && total > 0) {
                homeProb = Math.round(homeProb * 100 / total);
                awayProb = 100 - homeProb;
            }
            
            const confidenceText = Number.isFinite(confidence) ? `${confidence}` : 'N/A';
            
            const homeWinner = homeProb > awayProb;
            const awayWinner = awayProb > homeProb;
            
            predictionDiv.innerHTML = `
                <div class="prediction">
                    <div class="win-probabilities">
                        <div class="probability ${awayWinner ? 'winner' : ''}">
                            <div class="probability-label">${getTeamEmoji(data.away_team)} ${data.away_team} ${getTeamEmoji(data.away_team)}</div>
                            <div class="probability-value">${awayProb}% ✈️</div>
                        </div>
                        <div class="probability ${homeWinner ? 'winner' : ''}">
                            <div class="probability-label">${getTeamEmoji(data.home_team)} ${data.home_team} ${getTeamEmoji(data.home_team)}</div>
                            <div class="probability-value">${homeProb}% 🏠</div>
                        </div>
                    </div>
                    <div class="confidence">
                        🎯 Confidence: ${confidenceText}/10
                    </div>
                    <div class="analysis-text">
                        ${formatAnalysis(analysis)}
                    </div>
                </div>
            `;
        }

        function formatAnalysis(text) {
            if (!text) return '';
            const lines = text.split(/\\n/);
            let html = '';
            let inList = false;
            for (let raw of lines) {
                const line = raw.trim();
                if (!line) continue;
                // Headings like **Projected Impact Players**:
                    const hdr = line.match(/^\\*\\*(.+?)\\*\\*:?\\s*$/);
                if (hdr) {
                    if (inList) { html += '</ul>'; inList = false; }
                    html += `<h4>${hdr[1]}</h4>`;
                    continue;
                }
                const m = line.match(/^-\\s+(.+)/);
                if (m) {
                    if (!inList) { html += '<ul>'; inList = true; }
                    const item = m[1].replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>');
                    html += `<li>${item}</li>`;
                } else {
                    if (inList) { html += '</ul>'; inList = false; }
                    const paragraph = line.replace(/\\*\\*(.+?)\\*\\*/g, '<strong>$1</strong>');
                    html += `<p>${paragraph}</p>`;
                }
            }
            if (inList) { html += '</ul>'; }
            return html;
        }

        window.addEventListener('load', loadTodaysGames);
    </script>
</body>
</html>
"""
