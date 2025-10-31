"""
Analytics dashboard HTML template with Chart.js visualizations
"""

def get_analytics_html_template():
    """Returns the HTML template for the analytics dashboard"""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SkateIQ Analytics — Prediction Performance Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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
            max-width: 1400px;
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

        /* Navigation */
        .nav {
            display: flex;
            justify-content: center;
            gap: 16px;
            margin-bottom: 32px;
        }

        .nav-link {
            padding: 12px 24px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            text-decoration: none;
            color: var(--text-primary);
            font-weight: 500;
            transition: var(--transition);
            box-shadow: var(--shadow-sm);
        }

        .nav-link:hover {
            background: white;
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }

        .nav-link.active {
            background: var(--accent);
            color: white;
            border-color: var(--accent);
        }

        /* Chart Grid */
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 24px;
            margin-bottom: 32px;
        }

        .chart-card {
            background: var(--bg-card);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border-radius: var(--radius);
            border: 1px solid var(--border);
            padding: 24px;
            box-shadow: var(--shadow-sm);
            transition: var(--transition);
        }

        .chart-card:hover {
            transform: translateY(-4px);
            box-shadow: var(--shadow-lg);
        }

        .chart-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 16px;
            color: var(--text-primary);
        }

        .chart-container {
            position: relative;
            width: 100%;
            height: 300px;
        }

        /* Stats Cards */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
        }

        .stat-card {
            background: var(--bg-card);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            padding: 24px;
            border-radius: 16px;
            border: 1px solid var(--border);
            text-align: center;
            box-shadow: var(--shadow-sm);
            transition: var(--transition);
        }

        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }

        .stat-value {
            font-size: 36px;
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent), #34c759);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 8px;
        }

        .stat-label {
            font-size: 14px;
            color: var(--text-secondary);
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .stat-description {
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 4px;
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

        /* Responsive */
        @media (max-width: 768px) {
            h1 {
                font-size: 36px;
            }

            .charts-grid {
                grid-template-columns: 1fr;
            }

            .nav {
                flex-direction: column;
                align-items: center;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">📊</div>
            <h1>SkateIQ Analytics</h1>
            <p class="subtitle">Prediction Performance Dashboard</p>
        </header>

        <nav class="nav">
            <a href="/" class="nav-link">🏒 Predictions</a>
            <a href="/analytics" class="nav-link active">📊 Analytics</a>
        </nav>

        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p class="loading-text">Loading analytics data...</p>
        </div>

        <div id="content" style="display: none;">
            <!-- Stats Overview -->
            <div class="stats-grid" id="statsGrid">
                <!-- Dynamic stats cards will be inserted here -->
            </div>

            <!-- Charts Grid -->
            <div class="charts-grid">
                <div class="chart-card">
                    <h3 class="chart-title">Accuracy Trends (Last 30 Days)</h3>
                    <div class="chart-container">
                        <canvas id="accuracyTrendChart"></canvas>
                    </div>
                </div>

                <div class="chart-card">
                    <h3 class="chart-title">Confidence vs Accuracy</h3>
                    <div class="chart-container">
                        <canvas id="confidenceChart"></canvas>
                    </div>
                </div>

                <div class="chart-card">
                    <h3 class="chart-title">Home vs Away Predictions</h3>
                    <div class="chart-container">
                        <canvas id="homeAwayChart"></canvas>
                    </div>
                </div>

                <div class="chart-card">
                    <h3 class="chart-title">Top Team Performance</h3>
                    <div class="chart-container">
                        <canvas id="teamPerformanceChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Chart configurations
        const chartConfig = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 20
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                }
            }
        };

        let charts = {};

        async function loadAnalytics() {
            try {
                // Load all analytics data
                const [
                    accuracyTrends,
                    confidenceAnalysis,
                    teamPerformance,
                    streaks,
                    homeAway
                ] = await Promise.all([
                    fetch('/api/analytics/accuracy-trends?days=30').then(r => r.json()),
                    fetch('/api/analytics/confidence-analysis').then(r => r.json()),
                    fetch('/api/analytics/team-performance?limit=10').then(r => r.json()),
                    fetch('/api/analytics/streaks').then(r => r.json()),
                    fetch('/api/analytics/home-away').then(r => r.json())
                ]);

                // Create stats cards
                createStatsCards(streaks, homeAway);

                // Create charts
                createAccuracyTrendChart(accuracyTrends);
                createConfidenceChart(confidenceAnalysis);
                createHomeAwayChart(homeAway);
                createTeamPerformanceChart(teamPerformance);

                // Hide loading and show content
                document.getElementById('loading').style.display = 'none';
                document.getElementById('content').style.display = 'block';

            } catch (error) {
                console.error('Error loading analytics:', error);
                document.getElementById('loading').innerHTML = `
                    <div class="error">
                        <h3>Error Loading Analytics</h3>
                        <p>${error.message}</p>
                    </div>
                `;
            }
        }

        function createStatsCards(streaks, homeAway) {
            const statsGrid = document.getElementById('statsGrid');
            
            const currentStreak = streaks.current_streak;
            const streakText = currentStreak.type === 'correct' ? '🔥' : currentStreak.type === 'incorrect' ? '❄️' : '➖';
            
            statsGrid.innerHTML = `
                <div class="stat-card">
                    <div class="stat-value">${currentStreak.count}</div>
                    <div class="stat-label">Current Streak</div>
                    <div class="stat-description">${streakText} ${currentStreak.type}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${streaks.longest_correct_streak}</div>
                    <div class="stat-label">Best Streak</div>
                    <div class="stat-description">🔥 Longest correct</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${homeAway.home_predictions.accuracy}%</div>
                    <div class="stat-label">Home Accuracy</div>
                    <div class="stat-description">🏠 ${homeAway.home_predictions.total} predictions</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${homeAway.away_predictions.accuracy}%</div>
                    <div class="stat-label">Away Accuracy</div>
                    <div class="stat-description">✈️ ${homeAway.away_predictions.total} predictions</div>
                </div>
            `;
        }

        function createAccuracyTrendChart(data) {
            const ctx = document.getElementById('accuracyTrendChart').getContext('2d');
            
            charts.accuracyTrend = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.dates,
                    datasets: [{
                        label: 'Daily Accuracy %',
                        data: data.accuracies,
                        borderColor: '#0071e3',
                        backgroundColor: 'rgba(0, 113, 227, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    ...chartConfig,
                    scales: {
                        ...chartConfig.scales,
                        y: {
                            ...chartConfig.scales.y,
                            max: 100,
                            ticks: {
                                callback: function(value) {
                                    return value + '%';
                                }
                            }
                        }
                    }
                }
            });
        }

        function createConfidenceChart(data) {
            const ctx = document.getElementById('confidenceChart').getContext('2d');
            
            charts.confidence = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.confidence_levels,
                    datasets: [{
                        label: 'Accuracy %',
                        data: data.accuracies,
                        backgroundColor: 'rgba(0, 113, 227, 0.8)',
                        borderColor: '#0071e3',
                        borderWidth: 1
                    }]
                },
                options: {
                    ...chartConfig,
                    scales: {
                        ...chartConfig.scales,
                        y: {
                            ...chartConfig.scales.y,
                            max: 100,
                            ticks: {
                                callback: function(value) {
                                    return value + '%';
                                }
                            }
                        }
                    }
                }
            });
        }

        function createHomeAwayChart(data) {
            const ctx = document.getElementById('homeAwayChart').getContext('2d');
            
            charts.homeAway = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Home Predictions', 'Away Predictions'],
                    datasets: [{
                        data: [data.home_predictions.total, data.away_predictions.total],
                        backgroundColor: ['#0071e3', '#34c759'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                usePointStyle: true,
                                padding: 20
                            }
                        }
                    }
                }
            });
        }

        function createTeamPerformanceChart(data) {
            const ctx = document.getElementById('teamPerformanceChart').getContext('2d');
            
            const teams = data.best_teams.slice(0, 8); // Top 8 teams
            
            charts.teamPerformance = new Chart(ctx, {
                type: 'horizontalBar',
                data: {
                    labels: teams.map(t => t.team.replace(/^[^\\s]+ /, '')), // Remove city names for space
                    datasets: [{
                        label: 'Accuracy %',
                        data: teams.map(t => t.accuracy),
                        backgroundColor: teams.map((t, i) => 
                            `hsla(${200 + i * 15}, 70%, 50%, 0.8)`
                        ),
                        borderWidth: 1
                    }]
                },
                options: {
                    ...chartConfig,
                    indexAxis: 'y',
                    scales: {
                        x: {
                            beginAtZero: true,
                            max: 100,
                            ticks: {
                                callback: function(value) {
                                    return value + '%';
                                }
                            }
                        }
                    }
                }
            });
        }

        // Load analytics on page load
        window.addEventListener('load', loadAnalytics);
    </script>
</body>
</html>
"""