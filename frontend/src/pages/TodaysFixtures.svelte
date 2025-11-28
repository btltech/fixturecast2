<script>
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import { API_URL, ML_API_URL } from "../config.js";
  import SkeletonLoader from "../components/SkeletonLoader.svelte";
  import SearchBar from "../components/SearchBar.svelte";
  import ConfidenceBadge from "../components/ConfidenceBadge.svelte";
  import { getCurrentSeason } from "../services/season.js";
  import { getSavedSeason } from "../services/preferences.js";

  // League info for display
  const leagueInfo = {
    39: { name: "Premier League", emoji: "🏴󠁧󠁢󠁥󠁮󠁧󠁿" },
    140: { name: "La Liga", emoji: "🇪🇸" },
    135: { name: "Serie A", emoji: "🇮🇹" },
    78: { name: "Bundesliga", emoji: "🇩🇪" },
    61: { name: "Ligue 1", emoji: "🇫🇷" },
    88: { name: "Eredivisie", emoji: "🇳🇱" },
    94: { name: "Primeira Liga", emoji: "🇵🇹" },
    2: { name: "Champions League", emoji: "🏆" },
    3: { name: "Europa League", emoji: "🏆" },
    848: { name: "Conference League", emoji: "🥉" },
    40: { name: "Championship", emoji: "🏴󠁧󠁢󠁥󠁮󠁧󠁿" },
    141: { name: "Segunda División", emoji: "🇪🇸" },
    136: { name: "Serie B", emoji: "🇮🇹" },
    79: { name: "2. Bundesliga", emoji: "🇩🇪" },
    62: { name: "Ligue 2", emoji: "🇫🇷" },
    45: { name: "FA Cup", emoji: "🏆" },
    48: { name: "League Cup", emoji: "🏆" },
  };

  function getLeagueDisplay(leagueId) {
    return leagueInfo[leagueId] || { name: "League", emoji: "⚽" };
  }

  let todaysMatches = [];
  let matchOfTheDay = null;
  let loading = true;
  let error = null;
  let searchQuery = "";
  const season = getSavedSeason(getCurrentSeason());

  // Predictions state
  let predictions = {};
  let loadingPredictions = {};

  // Group matches by league
  $: matchesByLeague = groupByLeague(filteredMatches);

  function groupByLeague(matches) {
    const grouped = {};
    for (const match of matches) {
      const leagueId = match.league?.id || 0;
      if (!grouped[leagueId]) {
        grouped[leagueId] = [];
      }
      grouped[leagueId].push(match);
    }
    return grouped;
  }

  $: filteredMatches = todaysMatches.filter((fixture) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const home = fixture.teams.home.name.toLowerCase();
    const away = fixture.teams.away.name.toLowerCase();
    const league = (fixture.league?.name || "").toLowerCase();
    return home.includes(q) || away.includes(q) || league.includes(q);
  });

  function formatTime(dateStr) {
    return new Date(dateStr).toLocaleTimeString("en-GB", {
      timeZone: "Europe/London",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  async function loadTodaysFixtures() {
    loading = true;
    error = null;

    try {
      const res = await fetch(`${API_URL}/api/fixtures/today`);
      if (res.ok) {
        const data = await res.json();
        todaysMatches = data.response || [];
        matchOfTheDay = data.match_of_the_day;
      } else {
        error = "Failed to load today's fixtures";
      }
    } catch (e) {
      console.error("Error loading today's matches:", e);
      error = "Could not load today's matches";
    } finally {
      loading = false;
    }
  }

  async function loadPrediction(fixtureId, leagueId) {
    if (predictions[fixtureId] || loadingPredictions[fixtureId]) {
      return;
    }

    loadingPredictions[fixtureId] = true;
    loadingPredictions = { ...loadingPredictions };

    try {
      const res = await fetch(
        `${ML_API_URL}/api/prediction/${fixtureId}?league=${leagueId}&season=${season}`
      );

      if (res.ok) {
        const data = await res.json();
        predictions[fixtureId] = data.prediction;
        predictions = { ...predictions };
      }
    } catch (e) {
      console.error(`Error loading prediction for ${fixtureId}:`, e);
    } finally {
      loadingPredictions[fixtureId] = false;
      loadingPredictions = { ...loadingPredictions };
    }
  }

  function getPredictionSummary(pred) {
    if (!pred) return null;

    const homeProb = pred.home_win_prob * 100;
    const drawProb = pred.draw_prob * 100;
    const awayProb = pred.away_win_prob * 100;

    if (homeProb > awayProb && homeProb > drawProb) {
      return { winner: "home", prob: homeProb, label: "Home Win" };
    } else if (awayProb > homeProb && awayProb > drawProb) {
      return { winner: "away", prob: awayProb, label: "Away Win" };
    } else {
      return { winner: "draw", prob: drawProb, label: "Draw" };
    }
  }

  onMount(() => {
    loadTodaysFixtures();
  });
</script>

<div class="page-enter space-y-6 pb-12">
  <!-- Header -->
  <div class="flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl lg:text-3xl font-display font-bold flex items-center gap-3">
          <span class="text-3xl">📅</span>
          Today's Fixtures
        </h1>
        <p class="text-slate-400 mt-1">
          All matches playing today across major leagues • {new Date().toLocaleDateString("en-GB", {
            weekday: "long",
            day: "numeric",
            month: "long",
            year: "numeric",
          })}
        </p>
      </div>
      <button
        on:click={loadTodaysFixtures}
        class="p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
        title="Refresh fixtures"
      >
        <svg
          class="w-5 h-5 {loading ? 'animate-spin' : ''}"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
      </button>
    </div>

    <!-- Search -->
    <div class="max-w-md">
      <input
        type="text"
        bind:value={searchQuery}
        placeholder="Search teams or leagues..."
        class="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-400 focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50"
      />
    </div>
  </div>

  {#if loading}
    <!-- Loading State -->
    <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {#each Array(9) as _}
        <SkeletonLoader type="fixture" />
      {/each}
    </div>
  {:else if error}
    <!-- Error State -->
    <div class="glass-card p-12 text-center">
      <div class="text-4xl mb-4">⚠️</div>
      <h3 class="font-display font-bold text-xl mb-2 text-red-400">{error}</h3>
      <button
        on:click={loadTodaysFixtures}
        class="mt-4 px-6 py-2 bg-primary/20 hover:bg-primary/30 text-primary rounded-lg font-medium"
      >
        Try Again
      </button>
    </div>
  {:else if todaysMatches.length === 0}
    <!-- No Matches -->
    <div class="glass-card p-12 text-center">
      <div class="text-6xl mb-4">😴</div>
      <h3 class="font-display font-bold text-xl mb-2">No Matches Today</h3>
      <p class="text-slate-400 mb-4">
        There are no fixtures scheduled for today across major leagues.
      </p>
      <Link
        to="/fixtures"
        class="inline-flex items-center gap-2 px-6 py-3 bg-primary/20 hover:bg-primary/30 text-primary rounded-lg font-medium"
      >
        Browse Upcoming Fixtures
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </Link>
    </div>
  {:else}
    <!-- Match of the Day Highlight -->
    {#if matchOfTheDay}
      <div class="glass-card p-6 border-amber-500/30 bg-gradient-to-r from-amber-500/10 to-transparent">
        <div class="flex items-center gap-2 mb-4">
          <span class="text-amber-400 text-xl">⭐</span>
          <h2 class="font-display font-bold text-lg text-amber-400">Match of the Day</h2>
        </div>

        <Link
          to={`/prediction/${matchOfTheDay.fixture.id}?league=${matchOfTheDay.league?.id || 39}&season=${season}`}
          class="block group"
        >
          <div class="flex items-center justify-between">
            <!-- Home Team -->
            <div class="flex-1 text-center">
              <img
                src={matchOfTheDay.teams.home.logo}
                alt={matchOfTheDay.teams.home.name}
                class="w-16 h-16 mx-auto mb-2 group-hover:scale-110 transition-transform"
              />
              <div class="font-bold">{matchOfTheDay.teams.home.name}</div>
            </div>

            <!-- VS & Time -->
            <div class="px-6 text-center">
              <div class="text-xs text-slate-400 mb-1">
                {getLeagueDisplay(matchOfTheDay.league?.id).emoji}
                {matchOfTheDay.league?.name}
              </div>
              <div class="text-2xl font-display font-bold text-primary">
                {formatTime(matchOfTheDay.fixture.date)}
              </div>
              <div class="text-xs text-slate-400">UK Time</div>
            </div>

            <!-- Away Team -->
            <div class="flex-1 text-center">
              <img
                src={matchOfTheDay.teams.away.logo}
                alt={matchOfTheDay.teams.away.name}
                class="w-16 h-16 mx-auto mb-2 group-hover:scale-110 transition-transform"
              />
              <div class="font-bold">{matchOfTheDay.teams.away.name}</div>
            </div>
          </div>

          <div class="mt-4 text-center">
            <span class="inline-flex items-center gap-2 px-4 py-2 bg-amber-500/20 text-amber-400 rounded-full text-sm font-medium group-hover:bg-amber-500/30 transition-colors">
              🔮 View AI Analysis
            </span>
          </div>
        </Link>
      </div>
    {/if}

    <!-- Summary -->
    <div class="flex items-center justify-between px-2">
      <p class="text-sm text-slate-400">
        {filteredMatches.length} match{filteredMatches.length !== 1 ? "es" : ""} playing today
      </p>
      <p class="text-xs text-slate-500">
        {Object.keys(matchesByLeague).length} league{Object.keys(matchesByLeague).length !== 1 ? "s" : ""}
      </p>
    </div>

    <!-- Matches by League -->
    {#each Object.entries(matchesByLeague) as [leagueId, matches]}
      {@const league = getLeagueDisplay(parseInt(leagueId))}
      <div class="space-y-3">
        <div class="flex items-center gap-2 px-2">
          <span class="text-xl">{league.emoji}</span>
          <h2 class="font-display font-bold text-lg">{matches[0]?.league?.name || league.name}</h2>
          <span class="text-xs text-slate-400 bg-white/5 px-2 py-0.5 rounded-full">
            {matches.length} match{matches.length !== 1 ? "es" : ""}
          </span>
        </div>

        <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {#each matches as fixture (fixture.fixture.id)}
            {@const fixtureId = fixture.fixture.id}
            {@const leagueIdNum = fixture.league?.id || 39}
            {@const pred = predictions[fixtureId]}
            {@const summary = getPredictionSummary(pred)}

            <div class="glass-card p-4 relative overflow-hidden group">
              <!-- Match Time Header -->
              <div class="flex items-center justify-between mb-3">
                <span class="text-sm text-accent font-mono font-bold">
                  {formatTime(fixture.fixture.date)} UK
                </span>
                <span class="text-xs text-slate-500">
                  {fixture.fixture.venue?.name || ""}
                </span>
              </div>

              <!-- Teams -->
              <div class="flex items-center justify-between mb-4">
                <!-- Home Team -->
                <div class="flex-1 text-center">
                  <img
                    src={fixture.teams.home.logo}
                    alt={fixture.teams.home.name}
                    class="w-12 h-12 mx-auto mb-2"
                  />
                  <div class="font-medium text-sm truncate px-1">
                    {fixture.teams.home.name}
                  </div>
                </div>

                <!-- VS -->
                <div class="px-3 text-center">
                  <div class="text-xl font-bold text-slate-500">vs</div>
                </div>

                <!-- Away Team -->
                <div class="flex-1 text-center">
                  <img
                    src={fixture.teams.away.logo}
                    alt={fixture.teams.away.name}
                    class="w-12 h-12 mx-auto mb-2"
                  />
                  <div class="font-medium text-sm truncate px-1">
                    {fixture.teams.away.name}
                  </div>
                </div>
              </div>

              <!-- Prediction Section -->
              {#if pred}
                <div class="bg-gradient-to-r from-accent/10 to-purple-500/10 rounded-lg p-3 border border-accent/20">
                  <div class="flex justify-between items-center mb-2">
                    <span class="text-xs text-slate-400">AI Prediction</span>
                    <ConfidenceBadge confidence={summary.prob / 100} size="sm" showLabel={false} />
                  </div>
                  <div class="flex justify-between items-center text-xs mb-2">
                    <span class="font-medium {summary.winner === 'home' ? 'text-emerald-400' : summary.winner === 'away' ? 'text-rose-400' : 'text-slate-300'}">
                      {summary.label}
                    </span>
                    <span class="text-accent font-bold">{summary.prob.toFixed(0)}%</span>
                  </div>
                  <div class="flex gap-1 h-2 rounded-full overflow-hidden bg-slate-700">
                    <div
                      class="bg-green-500 transition-all"
                      style="width: {pred.home_win_prob * 100}%"
                    ></div>
                    <div
                      class="bg-slate-400 transition-all"
                      style="width: {pred.draw_prob * 100}%"
                    ></div>
                    <div
                      class="bg-red-500 transition-all"
                      style="width: {pred.away_win_prob * 100}%"
                    ></div>
                  </div>
                  <Link
                    to={`/prediction/${fixtureId}?league=${leagueIdNum}&season=${season}`}
                    class="block mt-3 text-center py-2 bg-accent/20 hover:bg-accent/30 text-accent rounded-lg text-sm font-medium"
                  >
                    🔮 View Full Analysis
                  </Link>
                </div>
              {:else}
                <button
                  on:click={() => loadPrediction(fixtureId, leagueIdNum)}
                  disabled={loadingPredictions[fixtureId]}
                  class="w-full py-3 bg-accent/20 hover:bg-accent/30 text-accent rounded-lg font-medium text-sm flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {#if loadingPredictions[fixtureId]}
                    <svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Loading...
                  {:else}
                    🧠 Get AI Prediction
                  {/if}
                </button>
              {/if}
            </div>
          {/each}
        </div>
      </div>
    {/each}
  {/if}
</div>
