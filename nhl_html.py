def get_html_template():
    """Returns the HTML template for the daily predictions page - Ultra modern Apple-inspired design"""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SkateIQ — Daily NHL Predictions</title>
    <style>
        :root {
            --bg-primary: #f5f5f7;
            --bg-card: rgba(255, 255, 255, 0.85);
            --text-primary: #1d1d1f;
            --text-secondary: #6e6e73;
            --accent: #0071e3;
            --accent-hover: #0077ed;
            --border: rgba(0, 0, 0, 0.06);
            --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.04);
            --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.08);
            --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.12);
            --radius: 18px;
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            padding: 20px;
            min-height: 100vh;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        /* Header */
        header {
            text-align: center;
            margin-bottom: 48px;
            padding: 48px 32px;
            background: var(--bg-card);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border-radius: var(--radius);
            border: 1px solid var(--border);
            box-shadow: var(--shadow-sm);
        }

        .logo {
            width: 72px;
            height: 72px;
            margin: 0 auto 20px;
            background: linear-gradient(135deg, #0071e3 0%, #005bb5 100%);
            border-radius: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 36px;
            box-shadow: 0 4px 12px rgba(0, 113, 227, 0.2);
        }

        h1 {
            font-size: 48px;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 12px;
            background: linear-gradient(90deg, var(--text-primary) 0%, var(--text-secondary) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .subtitle {
            font-size: 19px;
            color: var(--text-secondary);
            font-weight: 400;
        }

        /* Controls */
        .controls {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 32px;
            gap: 16px;
            flex-wrap: wrap;
        }

        .accuracy-banner {
            background: linear-gradient(135deg, rgba(0, 113, 227, 0.08), rgba(52, 199, 89, 0.08));
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            padding: 20px 32px;
            border-radius: 16px;
            border: 1px solid rgba(0, 113, 227, 0.12);
            margin-bottom: 32px;
            display: flex;
            justify-content: space-around;
            align-items: center;
            box-shadow: var(--shadow-md);
            gap: 24px;
        }

        .accuracy-stat {
            text-align: center;
        }

        .accuracy-value {
            font-size: 36px;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent), #34c759);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 4px;
        }

        .accuracy-label {
            font-size: 13px;
            color: var(--text-secondary);
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .date-selector {
            background: var(--bg-card);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            padding: 12px 16px;
            border-radius: 12px;
            border: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 12px;
            box-shadow: var(--shadow-sm);
        }

        .date-selector label {
            font-size: 14px;
            font-weight: 500;
            color: var(--text-secondary);
        }

        .date-selector input[type="date"] {
            padding: 8px 12px;
            border-radius: 8px;
            border: 1px solid var(--border);
            font-family: inherit;
            font-size: 14px;
            background: white;
            color: var(--text-primary);
            cursor: pointer;
        }

        .date-selector input[type="date"]:focus {
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.1);
        }

        .date-badge {
            background: var(--bg-card);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            padding: 12px 24px;
            border-radius: 12px;
            border: 1px solid var(--border);
            font-size: 15px;
            font-weight: 500;
            color: var(--text-primary);
            box-shadow: var(--shadow-sm);
        }

        .btn-group {
            display: flex;
            gap: 12px;
        }

        .btn {
            padding: 12px 24px;
            border-radius: 12px;
            border: none;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition);
            font-family: inherit;
        }

        .btn-primary {
            background: var(--accent);
            color: white;
            box-shadow: 0 2px 8px rgba(0, 113, 227, 0.3);
        }

        .btn-primary:hover {
            background: var(--accent-hover);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 113, 227, 0.4);
        }

        .btn-secondary {
            background: var(--bg-card);
            color: var(--text-primary);
            border: 1px solid var(--border);
            box-shadow: var(--shadow-sm);
        }

        .btn-secondary:hover {
            background: white;
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none !important;
        }

        /* Loading */
        .loading {
            text-align: center;
            padding: 80px 20px;
        }

        .spinner {
            width: 48px;
            height: 48px;
            margin: 0 auto 20px;
            border: 3px solid var(--border);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .loading-text {
            font-size: 17px;
            color: var(--text-secondary);
        }

        /* Games Grid */
        .games-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
            gap: 24px;
        }

        .game-card {
            background: var(--bg-card);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border-radius: var(--radius);
            border: 1px solid var(--border);
            padding: 24px;
            box-shadow: var(--shadow-sm);
            transition: var(--transition);
        }

        .game-card:hover {
            transform: translateY(-4px);
            box-shadow: var(--shadow-lg);
        }

        .matchup {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border);
        }

        .team {
            display: flex;
            align-items: center;
            gap: 12px;
            flex: 1;
        }

        .team-icon {
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, rgba(0, 113, 227, 0.1), rgba(0, 113, 227, 0.05));
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            border: 1px solid var(--border);
        }

        .team-info {
            flex: 1;
        }

        .team-name {
            font-size: 17px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 4px;
        }

        .team-badge {
            font-size: 13px;
            color: var(--text-secondary);
            font-weight: 500;
        }

        .vs {
            font-size: 13px;
            font-weight: 600;
            color: var(--text-secondary);
            padding: 0 12px;
        }

        .game-time {
            text-align: center;
            font-size: 15px;
            color: var(--text-secondary);
            margin-bottom: 16px;
        }

        /* Predictions */
        .prediction-section {
            margin-top: 20px;
        }

        .probabilities {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 16px;
        }

        .probability {
            background: rgba(0, 113, 227, 0.04);
            padding: 16px;
            border-radius: 12px;
            text-align: center;
            border: 1px solid rgba(0, 113, 227, 0.08);
            transition: var(--transition);
        }

        .probability.winner {
            background: linear-gradient(135deg, rgba(0, 113, 227, 0.1), rgba(0, 113, 227, 0.05));
            border-color: rgba(0, 113, 227, 0.2);
        }

        .prob-label {
            font-size: 13px;
            color: var(--text-secondary);
            margin-bottom: 8px;
            font-weight: 500;
        }

        .prob-value {
            font-size: 32px;
            font-weight: 700;
            color: var(--accent);
        }

        .confidence-badge {
            text-align: center;
            padding: 12px;
            background: rgba(0, 0, 0, 0.03);
            border-radius: 10px;
            font-size: 14px;
            color: var(--text-secondary);
            margin-bottom: 16px;
        }

        /* Modal Styles */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(10px);
            animation: fadeIn 0.2s ease;
        }

        .modal.show {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .modal-content {
            background: var(--bg-card);
            backdrop-filter: blur(20px) saturate(180%);
            border-radius: var(--radius);
            max-width: 800px;
            width: 100%;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            animation: slideUp 0.3s ease;
            border: 1px solid var(--border);
        }

        @keyframes slideUp {
            from { transform: translateY(50px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        .modal-header {
            padding: 24px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            background: var(--bg-card);
            backdrop-filter: blur(20px) saturate(180%);
            z-index: 10;
        }

        .modal-title {
            font-size: 20px;
            font-weight: 700;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .modal-close {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            border: none;
            background: rgba(0, 0, 0, 0.05);
            color: var(--text-secondary);
            font-size: 20px;
            cursor: pointer;
            transition: var(--transition);
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .modal-close:hover {
            background: rgba(0, 0, 0, 0.1);
            color: var(--text-primary);
        }

        .modal-body {
            padding: 32px;
            background: linear-gradient(180deg, var(--bg-card) 0%, rgba(245, 245, 247, 0.5) 100%);
        }

        .analysis-button {
            width: 100%;
            margin-top: 16px;
        }

        .live-score {
            background: linear-gradient(135deg, rgba(52, 199, 89, 0.15), rgba(52, 199, 89, 0.08));
            border: 1px solid rgba(52, 199, 89, 0.3);
            padding: 20px;
            border-radius: 14px;
            margin: 20px 0;
            text-align: center;
            box-shadow: 0 4px 12px rgba(52, 199, 89, 0.1);
        }

        .live-score-header {
            font-size: 12px;
            color: #34c759;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 16px;
            font-weight: 700;
        }

        .live-score-matchup {
            display: flex;
            justify-content: space-around;
            align-items: center;
            font-size: 18px;
            font-weight: 700;
        }

        .live-score-team {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
        }

        .live-score-value {
            font-size: 42px;
            font-weight: 800;
            color: #34c759;
            text-shadow: 0 2px 4px rgba(52, 199, 89, 0.2);
        }

        .prediction-locked {
            background: linear-gradient(135deg, rgba(255, 149, 0, 0.12), rgba(255, 149, 0, 0.06));
            border: 1px solid rgba(255, 149, 0, 0.3);
            padding: 14px;
            border-radius: 12px;
            text-align: center;
            font-size: 14px;
            color: #ff9500;
            margin-bottom: 20px;
            font-weight: 600;
            box-shadow: 0 2px 8px rgba(255, 149, 0, 0.1);
        }

        .analysis {
            font-size: 15px;
            line-height: 1.8;
            color: var(--text-primary);
        }

        .analysis h4 {
            font-size: 16px;
            font-weight: 700;
            margin: 24px 0 12px 0;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 8px;
            padding-bottom: 8px;
            border-bottom: 2px solid var(--border);
        }

        .analysis h4::before {
            content: "•";
            color: var(--accent);
            font-size: 20px;
        }

        .analysis ul {
            margin-left: 24px;
            margin-top: 12px;
            list-style: none;
        }

        .analysis li {
            position: relative;
            padding-left: 20px;
            margin-bottom: 8px;
        }

        .analysis li::before {
            content: "→";
            position: absolute;
            left: 0;
            color: var(--accent);
            font-weight: 700;
        }

        .analysis p {
            margin-bottom: 12px;
        }

        .analysis strong {
            color: var(--accent);
            font-weight: 600;
        }

        .analysis li {
            margin-bottom: 6px;
        }

        .analysis strong {
            font-weight: 600;
            color: var(--text-primary);
        }

        /* Error */
        .error {
            background: rgba(255, 59, 48, 0.1);
            border: 1px solid rgba(255, 59, 48, 0.2);
            padding: 20px;
            border-radius: 12px;
            color: #d70015;
            text-align: center;
        }

        .no-games {
            text-align: center;
            padding: 80px 20px;
            background: var(--bg-card);
            border-radius: var(--radius);
            border: 1px solid var(--border);
        }

        .no-games h2 {
            font-size: 28px;
            margin-bottom: 12px;
            color: var(--text-primary);
        }

        .no-games p {
            color: var(--text-secondary);
            font-size: 17px;
        }

        /* Footer */
        footer {
            margin-top: 64px;
            padding: 32px;
            text-align: center;
            background: var(--bg-card);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border-radius: var(--radius);
            border: 1px solid var(--border);
            box-shadow: var(--shadow-sm);
        }

        footer p {
            color: var(--text-secondary);
            font-size: 15px;
            margin: 8px 0;
        }

        footer a {
            color: var(--accent);
            text-decoration: none;
            font-weight: 500;
            transition: var(--transition);
        }

        footer a:hover {
            color: var(--accent-hover);
        }

        /* Responsive */
        @media (max-width: 768px) {
            h1 {
                font-size: 36px;
            }

            .games-grid {
                grid-template-columns: 1fr;
            }

            .controls {
                flex-direction: column;
                align-items: stretch;
            }

            .btn-group {
                width: 100%;
            }

            .btn {
                flex: 1;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">🏒</div>
            <h1>SkateIQ</h1>
            <p class="subtitle">AI-Powered NHL Matchup Predictions</p>
        </header>

        <div class="accuracy-banner" id="accuracyBanner">
            <div class="accuracy-stat">
                <div class="accuracy-value" id="accuracyPercentage">—%</div>
                <div class="accuracy-label">Accuracy</div>
            </div>
            <div class="accuracy-stat">
                <div class="accuracy-value" id="correctPredictions">—</div>
                <div class="accuracy-label">Correct</div>
            </div>
            <div class="accuracy-stat">
                <div class="accuracy-value" id="totalPredictions">—</div>
                <div class="accuracy-label">Total</div>
            </div>
            <div class="accuracy-stat">
                <div class="accuracy-value" id="recentPredictions">—</div>
                <div class="accuracy-label">This Week</div>
            </div>
        </div>

        <div class="controls">
            <div class="date-selector">
                <label for="gameDate">Select Date:</label>
                <input type="date" id="gameDate" onchange="loadGamesByDate()">
            </div>
            <div class="date-badge" id="dateHeader">Loading today's games...</div>
            <div class="btn-group">
                <button class="btn btn-secondary" onclick="loadTodaysGames()">Today</button>
                <button class="btn btn-secondary" onclick="loadGamesByDate()">Refresh</button>
            </div>
        </div>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p class="loading-text">Fetching today's NHL schedule...</p>
        </div>

        <div class="games-grid" id="gamesGrid"></div>

        <!-- Analysis Modal -->
        <div class="modal" id="analysisModal">
            <div class="modal-content">
                <div class="modal-header">
                    <div class="modal-title">
                        <span>📊</span>
                        <span id="modalTeams">Detailed Analysis</span>
                    </div>
                    <button class="modal-close" onclick="closeModal()">×</button>
                </div>
                <div class="modal-body" id="modalAnalysisContent">
                    <!-- Analysis content will be inserted here -->
                </div>
            </div>
        </div>

        <footer>
            <p>Built with care by <strong>Ahmed Alami</strong></p>
            <p>
                <a href="https://github.com/A71as" target="_blank">@A71as on GitHub</a>
            </p>
        </footer>
    </div>

    <script>
        // Team emoji mapping
        const teamEmojis = {
            'Carolina Hurricanes': '🌀', 'Hurricanes': '🌀',
            'New Jersey Devils': '😈', 'Devils': '😈',
            'New York Rangers': '🗽', 'Rangers': '🗽',
            'New York Islanders': '🏝️', 'Islanders': '🏝️',
            'Philadelphia Flyers': '🧡', 'Flyers': '🧡',
            'Pittsburgh Penguins': '🐧', 'Penguins': '🐧',
            'Columbus Blue Jackets': '💥', 'Blue Jackets': '💥',
            'Washington Capitals': '🦅', 'Capitals': '🦅',
            'Boston Bruins': '🐻', 'Bruins': '🐻',
            'Florida Panthers': '🐆', 'Panthers': '🐆',
            'Toronto Maple Leafs': '🍁', 'Maple Leafs': '🍁',
            'Tampa Bay Lightning': '⚡', 'Lightning': '⚡',
            'Detroit Red Wings': '🪽', 'Red Wings': '🪽',
            'Buffalo Sabres': '⚔️', 'Sabres': '⚔️',
            'Ottawa Senators': '🏛️', 'Senators': '🏛️',
            'Montreal Canadiens': '⚜️', 'Canadiens': '⚜️',
            'Dallas Stars': '⭐', 'Stars': '⭐',
            'Colorado Avalanche': '🏔️', 'Avalanche': '🏔️',
            'Winnipeg Jets': '✈️', 'Jets': '✈️',
            'Minnesota Wild': '🌲', 'Wild': '🌲',
            'St. Louis Blues': '🎺', 'Blues': '🎺',
            'Nashville Predators': '🎸', 'Predators': '🎸',
            'Arizona Coyotes': '🌵', 'Coyotes': '🌵',
            'Chicago Blackhawks': '🪶', 'Blackhawks': '🪶',
            'Vegas Golden Knights': '⚔️', 'Golden Knights': '⚔️',
            'Edmonton Oilers': '🛢️', 'Oilers': '🛢️',
            'Los Angeles Kings': '👑', 'Kings': '👑',
            'Vancouver Canucks': '🐋', 'Canucks': '🐋',
            'Calgary Flames': '🔥', 'Flames': '🔥',
            'Seattle Kraken': '🦑', 'Kraken': '🦑',
            'Anaheim Ducks': '🦆', 'Ducks': '🦆',
            'San Jose Sharks': '🦈', 'Sharks': '🦈',
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
                const date = new Date(timeString);
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
        
        // Fetch and display accuracy stats
        async function fetchAccuracy() {
            try {
                const response = await fetch('/api/accuracy');
                const data = await response.json();
                
                if (data.success) {
                    const acc = data.accuracy;
                    document.getElementById('accuracyPercentage').textContent = 
                        acc.accuracy_percentage.toFixed(1) + '%';
                    document.getElementById('correctPredictions').textContent = 
                        acc.correct_predictions;
                    document.getElementById('totalPredictions').textContent = 
                        acc.total_predictions;
                    document.getElementById('recentPredictions').textContent = 
                        acc.recent_predictions.length;
                }
            } catch (error) {
                console.error('Error fetching accuracy:', error);
            }
        }
        
        // Initialize date picker with today's date
        function initializeDatePicker() {
            const today = new Date();
            const dateInput = document.getElementById('gameDate');
            
            // Set today as default
            dateInput.value = today.toISOString().split('T')[0];
            
            // Set min to today, max to 7 days from now
            dateInput.min = today.toISOString().split('T')[0];
            const maxDate = new Date();
            maxDate.setDate(today.getDate() + 7);
            dateInput.max = maxDate.toISOString().split('T')[0];
        }
        
        async function loadTodaysGames() {
            const today = new Date().toISOString().split('T')[0];
            document.getElementById('gameDate').value = today;
            await loadGamesByDate();
        }
        
        async function loadGamesByDate() {
            const dateInput = document.getElementById('gameDate');
            const selectedDate = dateInput.value;
            
            if (!selectedDate) {
                await loadTodaysGames();
                return;
            }
            
            try {
                const response = await fetch(`/api/games/${selectedDate}`);
                const data = await response.json();
                
                document.getElementById('loading').style.display = 'none';
                
                if (!data.success || !data.games || data.games.length === 0) {
                    document.getElementById('gamesGrid').innerHTML = `
                        <div class="no-games">
                            <h2>No NHL games scheduled for ${selectedDate}</h2>
                            <p>Try a different date!</p>
                        </div>
                    `;
                    const displayDate = new Date(selectedDate + 'T12:00:00');
                    document.getElementById('dateHeader').textContent = 
                        displayDate.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
                    return;
                }
                
                const displayDate = new Date(selectedDate + 'T12:00:00');
                document.getElementById('dateHeader').textContent = 
                    `${displayDate.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })} • ${data.games.length} Games`;
                
                const gamesGrid = document.getElementById('gamesGrid');
                gamesGrid.innerHTML = data.games.map((game, index) => `
                    <div class="game-card" id="game-${index}">
                        <div class="matchup">
                            <div class="team">
                                <div class="team-icon">${getTeamEmoji(game.away_team)}</div>
                                <div class="team-info">
                                    <div class="team-name">${game.away_team}</div>
                                    <div class="team-badge">Away</div>
                                </div>
                            </div>
                            <div class="vs">VS</div>
                            <div class="team">
                                <div class="team-icon">${getTeamEmoji(game.home_team)}</div>
                                <div class="team-info">
                                    <div class="team-name">${game.home_team}</div>
                                    <div class="team-badge">Home</div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="game-time">🕐 ${formatGameTime(game.time)}</div>
                        
                        <button class="btn btn-primary" style="width: 100%;" onclick="analyzeGame(${index}, '${game.home_team}', '${game.away_team}', ${game.game_id || 0})" id="btn-${index}">
                            Get AI Prediction
                        </button>
                        
                        <div id="prediction-${index}"></div>
                    </div>
                `).join('');
                
            } catch (error) {
                document.getElementById('loading').style.display = 'none';
                document.getElementById('gamesGrid').innerHTML = `
                    <div class="error">
                        <h3>Error Loading Games</h3>
                        <p>${error.message}</p>
                    </div>
                `;
            }
        }

        async function analyzeGame(index, homeTeam, awayTeam, gameId) {
            const btn = document.getElementById(`btn-${index}`);
            const predictionDiv = document.getElementById(`prediction-${index}`);
            
            btn.disabled = true;
            btn.textContent = 'Analyzing...';
            
            predictionDiv.innerHTML = `
                <div class="prediction-section">
                    <div style="text-align: center; padding: 20px;">
                        <div class="spinner" style="margin: 0 auto;"></div>
                        <p style="margin-top: 12px; color: var(--text-secondary);">Analyzing matchup...</p>
                    </div>
                </div>
            `;
            
            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        home_team: homeTeam,
                        away_team: awayTeam,
                        game_id: gameId
                    })
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Analysis failed');
                }
                
                const data = await response.json();
                displayPrediction(index, data);
                
                // Refresh accuracy after prediction
                await fetchAccuracy();
                
            } catch (error) {
                predictionDiv.innerHTML = `
                    <div class="error" style="margin-top: 16px;">
                        <h4>Prediction Error</h4>
                        <p>${error.message}</p>
                    </div>
                `;
            } finally {
                btn.disabled = false;
                btn.textContent = 'Refresh Prediction';
            }
        }

        function openModal(teams, analysis) {
            document.getElementById('modalTeams').textContent = teams;
            document.getElementById('modalAnalysisContent').innerHTML = formatAnalysis(analysis);
            document.getElementById('analysisModal').classList.add('show');
            document.body.style.overflow = 'hidden';
        }

        function closeModal() {
            document.getElementById('analysisModal').classList.remove('show');
            document.body.style.overflow = 'auto';
        }

        // Close modal when clicking outside
        document.getElementById('analysisModal')?.addEventListener('click', function(e) {
            if (e.target === this) {
                closeModal();
            }
        });

        function displayPrediction(index, data) {
            const predictionDiv = document.getElementById(`prediction-${index}`);
            const analysis = (data.analysis_text || data.analysis || '');
            
            let homeProb = Number.isFinite(data.home_prob) ? Number(data.home_prob) : null;
            let awayProb = Number.isFinite(data.away_prob) ? Number(data.away_prob) : null;
            let confidence = Number.isFinite(data.confidence) ? Number(data.confidence) : null;
            
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
            
            // Check if game has live scores
            let liveScoreHTML = '';
            if (data.live_home_score !== undefined && data.live_away_score !== undefined && data.game_status) {
                const statusLabel = data.game_status === 'FINAL' ? 'FINAL' : 'LIVE';
                const statusClass = data.game_status === 'FINAL' ? '' : ' 🔴';
                liveScoreHTML = `
                    <div class="live-score">
                        <div class="live-score-header">${statusLabel}${statusClass}</div>
                        <div class="live-score-matchup">
                            <div class="live-score-team">
                                <div>${getTeamEmoji(data.away_team)}</div>
                                <div class="live-score-value">${data.live_away_score}</div>
                            </div>
                            <div style="font-size: 24px; color: var(--text-secondary);">-</div>
                            <div class="live-score-team">
                                <div>${getTeamEmoji(data.home_team)}</div>
                                <div class="live-score-value">${data.live_home_score}</div>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            // Check if prediction is locked
            let lockedHTML = '';
            if (data.is_locked) {
                lockedHTML = '<div class="prediction-locked">🔒 Prediction Locked - Game Started</div>';
            }
            
            predictionDiv.innerHTML = `
                <div class="prediction-section">
                    ${lockedHTML}
                    ${liveScoreHTML}
                    <div class="probabilities">
                        <div class="probability ${awayWinner ? 'winner' : ''}">
                            <div class="prob-label">${getTeamEmoji(data.away_team)} ${data.away_team}</div>
                            <div class="prob-value">${awayProb}%</div>
                        </div>
                        <div class="probability ${homeWinner ? 'winner' : ''}">
                            <div class="prob-label">${getTeamEmoji(data.home_team)} ${data.home_team}</div>
                            <div class="prob-value">${homeProb}%</div>
                        </div>
                    </div>
                    <div class="confidence-badge">
                        Confidence: ${confidenceText}/10
                    </div>
                    <button class="btn btn-primary analysis-button" onclick="openModalForGame(${index})">
                        📊 View Detailed Analysis
                    </button>
                    <div id="analysis-data-${index}" style="display: none;">${analysis}</div>
                </div>
            `;
        }
        
        function openModalForGame(index) {
            const analysisText = document.getElementById(`analysis-data-${index}`).textContent;
            const gameCard = document.getElementById(`game-${index}`);
            const teams = gameCard ? gameCard.querySelector('.matchup')?.textContent.replace(/\\s+/g, ' ').trim() : 'Game Analysis';
            openModal(teams, analysisText);
        }

        function formatAnalysis(text) {
            if (!text) return '';
            const lines = text.split(/\\n/);
            let html = '';
            let inList = false;
            for (let raw of lines) {
                const line = raw.trim();
                if (!line) continue;
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

        window.addEventListener('load', async function() {
            initializeDatePicker();
            await fetchAccuracy();
            await loadTodaysGames();
        });
    </script>
</body>
</html>
"""
