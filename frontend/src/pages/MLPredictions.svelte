<script>
    import { onMount } from "svelte";
    import { slide } from "svelte/transition";
    import { mlClient } from "../services/mlPredictionClient.js";
    import { ML_API_URL, BACKEND_API_URL } from "../services/apiConfig.js";
    import MLPrediction from "../components/MLPrediction.svelte";
    import { getCurrentSeason } from "../services/season.js";
    import { getSavedLeague, saveLeague, getSavedSeason, saveSeason, getSavedOddsFormat, saveOddsFormat } from "../services/preferences.js";

    const BACKEND_API = BACKEND_API_URL;
    const ML_API = ML_API_URL;

    // All supported leagues
    const leagues = [
        // Top Leagues (Tier 1)
        { id: 39, name: "Premier League", country: "England", emoji: "🏴󠁧󠁢󠁥󠁮󠁧󠁿", tier: 1 },
        { id: 140, name: "La Liga", country: "Spain", emoji: "🇪🇸", tier: 1 },
        { id: 135, name: "Serie A", country: "Italy", emoji: "🇮🇹", tier: 1 },
        { id: 78, name: "Bundesliga", country: "Germany", emoji: "🇩🇪", tier: 1 },
        { id: 61, name: "Ligue 1", country: "France", emoji: "🇫🇷", tier: 1 },
        { id: 88, name: "Eredivisie", country: "Netherlands", emoji: "🇳🇱", tier: 1 },
        { id: 94, name: "Primeira Liga", country: "Portugal", emoji: "🇵🇹", tier: 1 },
        // Championship Leagues (Tier 2)
        { id: 40, name: "Championship", country: "England", emoji: "🏴󠁧󠁢󠁥󠁮󠁧󠁿", tier: 2 },
        { id: 141, name: "Segunda División", country: "Spain", emoji: "🇪🇸", tier: 2 },
        { id: 136, name: "Serie B", country: "Italy", emoji: "🇮🇹", tier: 2 },
        { id: 79, name: "2. Bundesliga", country: "Germany", emoji: "🇩🇪", tier: 2 },
        { id: 62, name: "Ligue 2", country: "France", emoji: "🇫🇷", tier: 2 },
        // European Competitions
        { id: 2, name: "Champions League", country: "Europe", emoji: "🏆", tier: 0 },
        { id: 3, name: "Europa League", country: "Europe", emoji: "🥈", tier: 0 },
        { id: 848, name: "Conference League", country: "Europe", emoji: "🥉", tier: 0 },
    ];

    let matches = [];
    let selectedMatch = null;
    let prediction = null;
    let analysis = null;
    let loading = false;
    let loadingMatches = true;
    let error = null;
    let mlApiStatus = "checking";
    let league = getSavedLeague(39); // Default: Premier League (persisted)
    let season = getSavedSeason(getCurrentSeason());
    let showLeagueDropdown = false;
    let showAnalysis = false; // For collapsible analysis section
    let fixturesRequestToken = 0;
    let predictionRequestToken = 0;
    let oddsFormat = getSavedOddsFormat("decimal");

    // Get current league info
    $: currentLeague = leagues.find(l => l.id === league) || leagues[0];

    onMount(async () => {
        // Persist defaults on load so they are available across pages
        saveLeague(league);
        saveSeason(season);
        saveOddsFormat(oddsFormat);
        // Check ML API health
        checkMLApi();

        // Load upcoming fixtures from backend
        await loadUpcomingMatches();
    });

    async function checkMLApi() {
        try {
            const health = await mlClient.getHealth();
            mlApiStatus = health.status === "healthy" ? "online" : "offline";
        } catch (err) {
            mlApiStatus = "offline";
        }
    }

    function handleClickOutside(event) {
        // Don't close if clicking inside the dropdown
        if (showLeagueDropdown && !event.target.closest('.league-selector')) {
            showLeagueDropdown = false;
        }
    }

    // Lightly humanise and de-duplicate the raw analysis text from the API
    function humanizeAnalysis(text) {
        if (!text) return [];

        const pieces = text
            .split(/\n+/)
            .flatMap(line => line.split(/[•\-]\s+/));

        const seen = new Set();
        const cleaned = [];

        for (const piece of pieces) {
            const trimmed = piece.trim().replace(/^[•\-\s]+/, "");
            if (!trimmed) continue;

            const normalized = trimmed.toLowerCase().replace(/[^a-z0-9\s]/g, "").trim();
            if (!normalized || seen.has(normalized)) continue;
            seen.add(normalized);

            const sentence =
                trimmed.charAt(0).toUpperCase() + trimmed.slice(1);
            cleaned.push(/[.!?]$/.test(sentence) ? sentence : `${sentence}.`);
        }

        return cleaned;
    }

    $: humanizedAnalysis = humanizeAnalysis(analysis);

    async function changeLeague(newLeagueId) {
        league = newLeagueId;
        saveLeague(newLeagueId);
        showLeagueDropdown = false;
        selectedMatch = null;
        prediction = null;
        analysis = null;
        error = null;
        showAnalysis = false;
        predictionRequestToken += 1; // invalidate in-flight prediction requests
        await loadUpcomingMatches();
    }

    async function loadUpcomingMatches() {
        loadingMatches = true;
        matches = [];
        const requestId = ++fixturesRequestToken;
        try {
            const response = await fetch(
                `${BACKEND_API}/api/fixtures?league=${league}&season=${season}&next=20`
            );

            if (!response.ok) {
                throw new Error("Failed to load fixtures");
            }

            const data = await response.json();

            // Transform API response to match expected format
            if (requestId === fixturesRequestToken && data.response && Array.isArray(data.response)) {
                matches = data.response
                    .filter(fixture => {
                        // Only show upcoming matches (not started)
                        return fixture.fixture.status?.short === 'NS' ||
                               fixture.fixture.status?.short === 'TBD';
                    })
                    .slice(0, 15); // Limit to 15 upcoming matches
            }
        } catch (err) {
            console.error("Error loading fixtures:", err);
            error = "Failed to load fixtures. Make sure backend API is running on port 8001.";
        } finally {
            if (requestId === fixturesRequestToken) {
                loadingMatches = false;
            }
        }
    }

    async function getPrediction(match) {
        selectedMatch = match;
        loading = true;
        error = null;
        prediction = null;
        analysis = null;
        const requestId = ++predictionRequestToken;

        try {
            const fixtureId = match.fixture.id;

            // Call the actual ML prediction API with current season
            const response = await fetch(
                `${ML_API}/api/prediction/${fixtureId}?league=${league}&season=${season}`
            );

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Prediction failed");
            }

            const data = await response.json();

            // Extract the prediction data and analysis
            if (requestId === predictionRequestToken) {
                if (data.prediction) {
                    prediction = data.prediction;
                } else {
                    prediction = data;
                }

                // Extract analysis if available
                if (data.analysis) {
                    analysis = data.analysis;
                }
            }
        } catch (err) {
            error = err.message;
            console.error("Prediction error:", err);
        } finally {
            if (requestId === predictionRequestToken) {
                loading = false;
            }
        }
    }
</script>

<svelte:window on:click={handleClickOutside} />

<div class="prediction-page page-enter">
    <div class="page-header element-enter">
        <h1>AI Match Predictions</h1>
        <div class="header-controls">
            <!-- League Selector -->
            <div class="league-selector">
                <button
                    class="league-selector-btn"
                    on:click|stopPropagation={() => showLeagueDropdown = !showLeagueDropdown}
                >
                    <span class="league-emoji">{currentLeague.emoji}</span>
                    <span class="league-name">{currentLeague.name}</span>
                    <svg class="dropdown-arrow {showLeagueDropdown ? 'open' : ''}" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M6 9l6 6 6-6"/>
                    </svg>
                </button>

                {#if showLeagueDropdown}
                    <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
                    <div class="league-dropdown" on:click|stopPropagation>
                        <!-- European Competitions -->
                        <div class="league-group">
                            <div class="league-group-title">🏆 European Competitions</div>
                            {#each leagues.filter(l => l.tier === 0) as l}
                                <button
                                    type="button"
                                    class="league-option {league === l.id ? 'active' : ''}"
                                    on:click={() => changeLeague(l.id)}
                                >
                                    <span>{l.emoji}</span>
                                    <span>{l.name}</span>
                                </button>
                            {/each}
                        </div>

                        <!-- Top Leagues -->
                        <div class="league-group">
                            <div class="league-group-title">⭐ Top Leagues</div>
                            {#each leagues.filter(l => l.tier === 1) as l}
                                <button
                                    type="button"
                                    class="league-option {league === l.id ? 'active' : ''}"
                                    on:click={() => changeLeague(l.id)}
                                >
                                    <span>{l.emoji}</span>
                                    <span>{l.name}</span>
                                </button>
                            {/each}
                        </div>

                        <!-- Second Division -->
                        <div class="league-group">
                            <div class="league-group-title">📋 Second Division</div>
                            {#each leagues.filter(l => l.tier === 2) as l}
                                <button
                                    type="button"
                                    class="league-option {league === l.id ? 'active' : ''}"
                                    on:click={() => changeLeague(l.id)}
                                >
                                    <span>{l.emoji}</span>
                                    <span>{l.name}</span>
                                </button>
                            {/each}
                        </div>
                    </div>
                {/if}
            </div>

            <div class="ml-status">
                <div class="status-indicator {mlApiStatus}">
                    <div class="pulse"></div>
                </div>
                <span>ML Engine: {mlApiStatus}</span>
            </div>
        </div>
    </div>

    <div class="content-grid element-enter stagger-1">
        <!-- Match List -->
        <div class="matches-panel">
            <h2>{currentLeague.emoji} {currentLeague.name} Fixtures</h2>

            {#if loadingMatches}
                <div class="loading-state-small">
                    <div class="spinner-small"></div>
                    <p>Loading fixtures...</p>
                </div>
            {:else if matches.length === 0}
                <div class="empty-state">
                    <p>No upcoming fixtures</p>
                </div>
            {:else}
                <div class="matches-list">
                    {#each matches as match}
                        <button
                            class="match-card {selectedMatch?.fixture.id ===
                            match.fixture.id
                                ? 'selected'
                                : ''}"
                            on:click={() => getPrediction(match)}
                        >
                            <div class="match-league">{match.league.name}</div>
                            <div class="match-teams">
                                <div class="team">
                                    <span class="team-name"
                                        >{match.teams.home.name}</span
                                    >
                                </div>
                                <div class="vs">vs</div>
                                <div class="team">
                                    <span class="team-name"
                                        >{match.teams.away.name}</span
                                    >
                                </div>
                            </div>
                            <div class="match-date">
                                {new Date(
                                    match.fixture.date,
                                ).toLocaleDateString("en-US", {
                                    weekday: "short",
                                    month: "short",
                                    day: "numeric",
                                    hour: "2-digit",
                                    minute: "2-digit",
                                })}
                            </div>
                            {#if match.fixture.status?.short === 'NS'}
                                <div class="match-status">Not Started</div>
                            {/if}
                        </button>
                    {/each}
                </div>
            {/if}
        </div>

        <!-- Prediction Display -->
        <div class="prediction-panel">
            {#if !selectedMatch}
                <div class="placeholder-state">
                    <div class="placeholder-icon">
                        <svg
                            width="64"
                            height="64"
                            viewBox="0 0 24 24"
                            fill="none"
                        >
                            <circle
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                stroke-width="2"
                            />
                            <path
                                d="M12 8V12L15 15"
                                stroke="currentColor"
                                stroke-width="2"
                                stroke-linecap="round"
                            />
                        </svg>
                    </div>
                    <h3>Select a Match</h3>
                    <p>
                        Choose a fixture from the list to see AI-powered
                        predictions
                    </p>
                </div>
            {:else if loading}
                <div class="loading-state">
                    <div class="spinner"></div>
                    <p>Generating AI prediction...</p>
                </div>
            {:else if error}
                <div class="error-state">
                    <div class="error-icon">⚠️</div>
                    <h3>Prediction Failed</h3>
                    <p>{error}</p>
                    {#if mlApiStatus === "offline"}
                        <p class="error-hint">
                            The ML API appears to be offline. Make sure the ML
                            server is running on port 8000.
                        </p>
                    {/if}
                    <button
                        class="retry-btn"
                        on:click={() => getPrediction(selectedMatch)}
                    >
                        Try Again
                    </button>
                </div>
            {:else if prediction}
                <div class="prediction-display">
                    <div class="match-info">
                        <h2>
                            {selectedMatch.teams.home.name} vs {selectedMatch
                                .teams.away.name}
                        </h2>
                        <p class="league-badge">{selectedMatch.league.name}</p>
                    </div>

                    <MLPrediction
                        {prediction}
                        homeTeam={selectedMatch.teams.home.name}
                        awayTeam={selectedMatch.teams.away.name}
                        homeTeamId={selectedMatch.teams.home.id}
                        awayTeamId={selectedMatch.teams.away.id}
                        leagueId={league}
                    />

                    {#if analysis}
                        <div class="analysis-section" class:expanded={showAnalysis}>
                            <button class="analysis-toggle" on:click={() => showAnalysis = !showAnalysis}>
                                <h3>
                                    <span class="analysis-icon">🤖</span>
                                    AI Analysis
                                </h3>
                                <svg class="toggle-arrow" class:open={showAnalysis} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M6 9l6 6 6-6"/>
                                </svg>
                            </button>
                            {#if showAnalysis}
                                <div class="analysis-content" transition:slide>
                                    {#if humanizedAnalysis.length > 0}
                                        <ul>
                                            {#each humanizedAnalysis as point}
                                                <li>{point}</li>
                                            {/each}
                                        </ul>
                                    {:else}
                                        <p>{analysis}</p>
                                    {/if}
                                </div>
                            {:else}
                                <p class="analysis-preview">
                                    {humanizedAnalysis[0] || analysis}
                                </p>
                            {/if}
                        </div>
                    {/if}

                    <div class="prediction-footer">
                        <p class="disclaimer">
                            ℹ️ Predictions are generated using an ensemble of 8
                            machine learning models trained on 5 seasons of
                            historical data.
                        </p>
                    </div>
                </div>
            {/if}
        </div>
    </div>
</div>

<style>
    .prediction-page {
        max-width: 1400px;
        margin: 0 auto;
        padding: 16px;
    }

    @media (min-width: 768px) {
        .prediction-page {
            padding: 24px;
        }
    }

    .page-header {
        display: flex;
        flex-direction: column;
        gap: 12px;
        margin-bottom: 20px;
        padding-bottom: 16px;
        border-bottom: 2px solid rgba(139, 92, 246, 0.2);
        position: relative;
        z-index: 10; /* Keep dropdown above the content grid */
    }

    @media (min-width: 640px) {
        .page-header {
            flex-direction: row;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 32px;
        }
    }

    .page-header h1 {
        margin: 0;
        font-size: 1.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #a78bfa, #ec4899);
        background-clip: text;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    @media (min-width: 640px) {
        .page-header h1 {
            font-size: 2rem;
        }
    }

    .header-controls {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        align-items: center;
    }

    /* League Selector Styles */
    .league-selector {
        position: relative;
    }

    .league-selector-btn {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
        background: rgba(139, 92, 246, 0.15);
        border: 1px solid rgba(139, 92, 246, 0.3);
        border-radius: 12px;
        color: white;
        cursor: pointer;
        transition: all 0.2s ease;
        font-size: 0.875rem;
    }

    .league-selector-btn:hover {
        background: rgba(139, 92, 246, 0.25);
        border-color: rgba(139, 92, 246, 0.5);
    }

    .league-emoji {
        font-size: 1.1rem;
    }

    .league-name {
        font-weight: 500;
    }

    .dropdown-arrow {
        transition: transform 0.2s ease;
    }

    .dropdown-arrow.open {
        transform: rotate(180deg);
    }

    .league-dropdown {
        position: absolute;
        top: calc(100% + 8px);
        left: 0;
        z-index: 120;
        min-width: 240px;
        max-height: 400px;
        overflow-y: auto;
        background: rgba(30, 30, 40, 0.98);
        border: 1px solid rgba(139, 92, 246, 0.3);
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        backdrop-filter: blur(10px);
    }

    .league-group {
        padding: 8px 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }

    .league-group:last-child {
        border-bottom: none;
    }

    .league-group-title {
        padding: 8px 16px;
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: rgba(255, 255, 255, 0.5);
    }

    .league-option {
        display: flex;
        align-items: center;
        gap: 10px;
        width: 100%;
        padding: 10px 16px;
        background: transparent;
        border: none;
        color: white;
        cursor: pointer;
        font-size: 0.875rem;
        text-align: left;
        transition: background 0.15s ease;
    }

    .league-option:hover {
        background: rgba(139, 92, 246, 0.2);
    }

    .league-option.active {
        background: rgba(139, 92, 246, 0.3);
        color: #a78bfa;
    }

    .ml-status {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 6px 12px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 20px;
        font-size: 0.75rem;
        width: fit-content;
    }

    @media (min-width: 640px) {
        .ml-status {
            padding: 8px 16px;
            font-size: 0.875rem;
        }
    }

    .status-indicator {
        position: relative;
        width: 10px;
        height: 10px;
        border-radius: 50%;
    }

    @media (min-width: 640px) {
        .status-indicator {
            width: 12px;
            height: 12px;
        }
    }

    .status-indicator.online {
        background: #10b981;
    }

    .status-indicator.offline {
        background: #ef4444;
    }

    .status-indicator.checking {
        background: #f59e0b;
    }

    .pulse {
        position: absolute;
        width: 100%;
        height: 100%;
        border-radius: 50%;
        background: inherit;
        animation: pulse 2s ease-in-out infinite;
    }

    @keyframes pulse {
        0%,
        100% {
            opacity: 1;
            transform: scale(1);
        }
        50% {
            opacity: 0;
            transform: scale(1.5);
        }
    }

    .content-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 16px;
    }

    @media (min-width: 1024px) {
        .content-grid {
            grid-template-columns: 380px 1fr;
            gap: 24px;
        }
    }

    @media (min-width: 1280px) {
        .content-grid {
            grid-template-columns: 400px 1fr;
        }
    }

    .matches-panel,
    .prediction-panel {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 16px;
        backdrop-filter: blur(10px);
    }

    @media (min-width: 640px) {
        .matches-panel,
        .prediction-panel {
            border-radius: 16px;
            padding: 20px;
        }
    }

    @media (min-width: 1024px) {
        .matches-panel,
        .prediction-panel {
            padding: 24px;
        }
    }

    .matches-panel h2 {
        margin: 0 0 16px 0;
        font-size: 1.125rem;
        font-weight: 700;
    }

    @media (min-width: 640px) {
        .matches-panel h2 {
            margin: 0 0 20px 0;
            font-size: 1.25rem;
        }
    }

    .matches-list {
        display: flex;
        flex-direction: column;
        gap: 10px;
        max-height: 60vh;
        overflow-y: auto;
        -webkit-overflow-scrolling: touch;
    }

    @media (min-width: 640px) {
        .matches-list {
            gap: 10px;
            max-height: none;
        }
    }

    .match-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 12px;
        cursor: pointer;
        transition: all 0.2s ease;
        text-align: left;
        width: 100%;
        min-height: 88px; /* Fixed minimum height for consistency */
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    @media (min-width: 640px) {
        .match-card {
            border-radius: 12px;
            padding: 16px;
            min-height: 96px; /* Slightly taller on desktop */
        }
    }

    .match-card:hover {
        background: rgba(139, 92, 246, 0.1);
        border-color: rgba(139, 92, 246, 0.3);
        transform: translateX(4px);
    }

    .match-card:active {
        transform: scale(0.98);
        background: rgba(139, 92, 246, 0.15);
    }

    .match-card.selected {
        background: rgba(139, 92, 246, 0.15);
        border-color: rgba(139, 92, 246, 0.5);
        box-shadow: 0 0 20px rgba(139, 92, 246, 0.2);
    }

    .match-league {
        font-size: 0.6875rem;
        color: var(--primary-400, #a78bfa);
        font-weight: 600;
        margin-bottom: 6px;
    }

    @media (min-width: 640px) {
        .match-league {
            font-size: 0.75rem;
            margin-bottom: 8px;
        }
    }

    .match-teams {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
    }

    @media (min-width: 640px) {
        .match-teams {
            gap: 12px;
            margin-bottom: 8px;
        }
    }

    .team {
        flex: 1;
        min-width: 0;
        max-width: 45%; /* Prevent overflow */
    }

    .team-name {
        font-weight: 600;
        font-size: 0.875rem;
        display: block;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 100%;
    }

    @media (min-width: 640px) {
        .team-name {
            font-size: 1rem;
        }
    }

    .vs {
        font-size: 0.6875rem;
        opacity: 0.6;
        font-weight: 700;
        flex-shrink: 0;
    }

    @media (min-width: 640px) {
        .vs {
            font-size: 0.75rem;
        }
    }

    .match-date {
        font-size: 0.75rem;
        opacity: 0.7;
    }

    @media (min-width: 640px) {
        .match-date {
            font-size: 0.8125rem;
        }
    }

    .match-status {
        font-size: 0.6875rem;
        margin-top: 4px;
        padding: 2px 6px;
        background: rgba(139, 92, 246, 0.2);
        border-radius: 6px;
        display: inline-block;
    }

    @media (min-width: 640px) {
        .match-status {
            font-size: 0.75rem;
            padding: 2px 8px;
            border-radius: 8px;
        }
    }

    .loading-state-small {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
        padding: 40px 20px;
        opacity: 0.7;
    }

    .spinner-small {
        width: 32px;
        height: 32px;
        border: 3px solid rgba(139, 92, 246, 0.2);
        border-top-color: #a78bfa;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }

    .empty-state {
        padding: 40px 20px;
        text-align: center;
        opacity: 0.6;
    }

    .placeholder-state,
    .loading-state,
    .error-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 300px;
        text-align: center;
        gap: 12px;
        padding: 20px;
    }

    @media (min-width: 640px) {
        .placeholder-state,
        .loading-state,
        .error-state {
            min-height: 500px;
            gap: 16px;
        }
    }

    .placeholder-icon {
        opacity: 0.3;
        color: var(--primary-400, #a78bfa);
    }

    .placeholder-icon svg {
        width: 48px;
        height: 48px;
    }

    @media (min-width: 640px) {
        .placeholder-icon svg {
            width: 64px;
            height: 64px;
        }
    }

    .placeholder-state h3,
    .error-state h3 {
        font-size: 1.125rem;
        margin: 0;
    }

    @media (min-width: 640px) {
        .placeholder-state h3,
        .error-state h3 {
            font-size: 1.25rem;
        }
    }

    .placeholder-state p,
    .error-state p {
        font-size: 0.875rem;
        opacity: 0.7;
        margin: 0;
    }

    .loading-state .spinner {
        width: 40px;
        height: 40px;
        border: 3px solid rgba(139, 92, 246, 0.2);
        border-top-color: #a78bfa;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }

    @media (min-width: 640px) {
        .loading-state .spinner {
            width: 48px;
            height: 48px;
            border-width: 4px;
        }
    }

    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }

    .error-icon {
        font-size: 2.5rem;
    }

    @media (min-width: 640px) {
        .error-icon {
            font-size: 3rem;
        }
    }

    .error-hint {
        font-size: 0.8125rem;
        opacity: 0.7;
        font-style: italic;
    }

    .retry-btn {
        margin-top: 12px;
        padding: 10px 20px;
        background: rgba(139, 92, 246, 0.2);
        border: 1px solid rgba(139, 92, 246, 0.5);
        border-radius: 8px;
        color: inherit;
        cursor: pointer;
        font-weight: 600;
        transition: all 0.2s ease;
        min-height: 44px;
    }

    @media (min-width: 640px) {
        .retry-btn {
            margin-top: 16px;
            padding: 10px 24px;
        }
    }

    .retry-btn:hover {
        background: rgba(139, 92, 246, 0.3);
        transform: scale(1.05);
    }

    .retry-btn:active {
        transform: scale(0.98);
    }

    .prediction-display {
        animation: fadeSlideIn 100ms var(--ease-smooth, cubic-bezier(0.25, 0.46, 0.45, 0.94)) forwards;
    }

    @keyframes fadeSlideIn {
        from {
            opacity: 0;
            transform: translateY(6px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .match-info {
        margin-bottom: 16px;
    }

    @media (min-width: 640px) {
        .match-info {
            margin-bottom: 24px;
        }
    }

    .match-info h2 {
        margin: 0 0 8px 0;
        font-size: 1.125rem;
        font-weight: 800;
    }

    @media (min-width: 640px) {
        .match-info h2 {
            font-size: 1.5rem;
        }
    }

    .league-badge {
        display: inline-block;
        padding: 4px 10px;
        background: rgba(139, 92, 246, 0.2);
        border-radius: 10px;
        font-size: 0.6875rem;
        font-weight: 600;
        color: var(--primary-300, #c4b5fd);
    }

    @media (min-width: 640px) {
        .league-badge {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.75rem;
        }
    }

    .analysis-section {
        margin-top: 16px;
        padding: 0;
        background: rgba(139, 92, 246, 0.05);
        border: 1px solid rgba(139, 92, 246, 0.2);
        border-radius: 10px;
        overflow: hidden;
        transition: all 0.2s ease;
    }

    .analysis-section.expanded {
        background: rgba(139, 92, 246, 0.08);
    }

    @media (min-width: 640px) {
        .analysis-section {
            margin-top: 24px;
            border-radius: 12px;
        }
    }

    .analysis-toggle {
        width: 100%;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px;
        background: transparent;
        border: none;
        cursor: pointer;
        color: inherit;
        transition: background 0.15s ease;
    }

    .analysis-toggle:hover {
        background: rgba(139, 92, 246, 0.1);
    }

    .analysis-toggle h3 {
        margin: 0;
        font-size: 1rem;
        font-weight: 700;
        color: var(--primary-300, #c4b5fd);
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .analysis-icon {
        font-size: 1.125rem;
    }

    .toggle-arrow {
        color: var(--primary-400, #a78bfa);
        transition: transform 0.2s ease;
    }

    .toggle-arrow.open {
        transform: rotate(180deg);
    }

    .analysis-preview {
        padding: 0 16px 16px;
        margin: 0;
        font-size: 0.8125rem;
        opacity: 0.7;
        line-height: 1.5;
    }

    @media (min-width: 640px) {
        .analysis-toggle {
            padding: 20px;
        }

        .analysis-toggle h3 {
            font-size: 1.125rem;
        }

        .analysis-icon {
            font-size: 1.25rem;
        }

        .analysis-preview {
            padding: 0 20px 20px;
        }
    }

    .analysis-content {
        padding: 0 16px 16px;
        line-height: 1.7;
        color: rgba(255, 255, 255, 0.85);
    }

    .analysis-content p {
        margin: 6px 0;
        font-size: 0.8125rem;
    }

    .analysis-content ul {
        padding-left: 1.1rem;
        margin: 0;
        list-style: disc;
        display: grid;
        gap: 6px;
    }

    .analysis-content li {
        margin: 0;
        font-size: 0.9rem;
        color: rgba(255, 255, 255, 0.9);
    }

    @media (min-width: 640px) {
        .analysis-content {
            line-height: 1.8;
        }

        .analysis-content p {
            margin: 8px 0;
            font-size: 0.9375rem;
        }
    }

    .analysis-content p:empty {
        display: none;
    }

    .prediction-footer {
        margin-top: 16px;
        padding-top: 12px;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
    }

    @media (min-width: 640px) {
        .prediction-footer {
            margin-top: 24px;
            padding-top: 16px;
        }
    }

    .disclaimer {
        font-size: 0.75rem;
        opacity: 0.6;
        margin: 0;
        line-height: 1.5;
    }

    @media (min-width: 640px) {
        .disclaimer {
            font-size: 0.8125rem;
        }
    }
</style>
