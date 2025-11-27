<script>
  import { Link } from "svelte-routing";
  import { onMount } from "svelte";
  import { API_URL } from "../config.js";
  import { getCurrentSeason } from "../services/season.js";
  import { getSavedSeason, saveSeason } from "../services/preferences.js";

  let matchOfTheDay = null;
  let todaysMatches = [];
  let loading = true;
  let error = null;
  const season = getSavedSeason(getCurrentSeason());

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
    40: { name: "Championship", emoji: "🏴󠁧󠁢󠁥󠁮󠁧󠁿" },
    141: { name: "Segunda División", emoji: "🇪🇸" },
    136: { name: "Serie B", emoji: "🇮🇹" },
    79: { name: "2. Bundesliga", emoji: "🇩🇪" },
    62: { name: "Ligue 2", emoji: "🇫🇷" },
  };

  function getLeagueDisplay(leagueId) {
    return leagueInfo[leagueId] || { name: "League", emoji: "⚽" };
  }

  onMount(async () => {
    saveSeason(season);
    try {
      // Fetch today's fixtures
      const res = await fetch(`${API_URL}/api/fixtures/today`);
      if (res.ok) {
        const data = await res.json();
        todaysMatches = data.response || [];
        matchOfTheDay = data.match_of_the_day;
      }
    } catch (e) {
      console.error("Error loading today's matches:", e);
      error = "Could not load today's matches";
    } finally {
      loading = false;
    }
  });

  function formatTime(dateStr) {
    return new Date(dateStr).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  }
</script>

<div class="space-y-6 md:space-y-8 page-enter">
  <!-- Hero Section -->
  <div
    class="glass-card p-6 md:p-8 lg:p-12 text-center relative overflow-hidden group"
  >
    <div
      class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-accent to-transparent"
    ></div>
    <div
      class="absolute inset-0 bg-accent/5 opacity-0 group-hover:opacity-10 transition-opacity duration-300"
    ></div>

    <h1 class="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-extrabold mb-3 md:mb-4 tracking-tight">
      <span
        class="text-transparent bg-clip-text bg-gradient-to-r from-white to-slate-400"
      >
        Fixture
      </span>
      <span
        class="text-transparent bg-clip-text bg-gradient-to-r from-accent to-purple-400"
      >
        Cast
      </span>
    </h1>

    <p class="text-sm sm:text-base md:text-lg text-slate-400 max-w-2xl mx-auto mb-6 md:mb-8 px-2">
      AI-powered football predictions for <strong class="text-white">today's matches</strong>.
      Get accurate forecasts generated on match day for maximum accuracy.
    </p>

    <div class="flex flex-col sm:flex-row justify-center gap-3 sm:gap-4">
      <Link
        to="/fixtures"
        class="px-6 sm:px-8 py-3 rounded-full bg-accent text-white font-bold btn-glow touch-target"
      >
        Today's Fixtures
      </Link>
      <Link
        to="/predictions"
        class="px-6 sm:px-8 py-3 rounded-full bg-white/10 text-white font-bold btn-press backdrop-blur-sm border border-white/10 touch-target"
      >
        AI Predictions
      </Link>
    </div>
  </div>

  <!-- Match of the Day Section -->
  {#if loading}
    <div class="glass-card p-8 text-center">
      <div class="inline-block w-10 h-10 border-4 border-accent border-t-transparent rounded-full loading-spin"></div>
      <p class="mt-4 text-slate-400 loading-pulse">Loading today's matches...</p>
    </div>
  {:else if matchOfTheDay}
    <div class="glass-card p-4 md:p-6 relative overflow-hidden content-enter">
      <!-- Spotlight effect -->
      <div class="absolute top-0 left-1/2 -translate-x-1/2 w-64 h-32 bg-accent/20 blur-3xl rounded-full"></div>

      <div class="relative">
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-2">
            <span class="text-2xl">⭐</span>
            <h2 class="text-lg md:text-xl font-bold text-accent">Match of the Day</h2>
          </div>
          <div class="text-xs md:text-sm text-slate-400">
            {getLeagueDisplay(matchOfTheDay.league?.id).emoji} {matchOfTheDay.league?.name || 'League'}
          </div>
        </div>

        <Link
          to={`/prediction/${matchOfTheDay.fixture.id}?league=${matchOfTheDay.league?.id || 39}&season=${season}`}
          class="block bg-gradient-to-r from-accent/10 to-purple-500/10 rounded-xl p-4 md:p-6 card-interactive border border-accent/20"
        >
          <div class="flex items-center justify-between">
            <!-- Home Team -->
            <div class="flex-1 text-center">
              <img
                src={matchOfTheDay.teams.home.logo}
                alt={matchOfTheDay.teams.home.name}
                class="w-16 h-16 md:w-20 md:h-20 mx-auto mb-2"
              />
              <div class="font-bold text-sm md:text-lg">{matchOfTheDay.teams.home.name}</div>
            </div>

            <!-- VS & Time -->
            <div class="px-4 md:px-8 text-center">
              <div class="text-2xl md:text-3xl font-extrabold text-slate-500 mb-1">VS</div>
              <div class="text-sm md:text-base text-accent font-mono">
                {formatTime(matchOfTheDay.fixture.date)}
              </div>
              <div class="text-xs text-slate-500 mt-1">
                {new Date(matchOfTheDay.fixture.date).toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })}
              </div>
            </div>

            <!-- Away Team -->
            <div class="flex-1 text-center">
              <img
                src={matchOfTheDay.teams.away.logo}
                alt={matchOfTheDay.teams.away.name}
                class="w-16 h-16 md:w-20 md:h-20 mx-auto mb-2"
              />
              <div class="font-bold text-sm md:text-lg">{matchOfTheDay.teams.away.name}</div>
            </div>
          </div>

          <div class="mt-4 text-center">
            <span class="inline-flex items-center gap-2 px-4 py-2 bg-accent/20 rounded-full text-sm text-accent font-medium btn-press">
              🧠 Get AI Prediction
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
              </svg>
            </span>
          </div>
        </Link>
      </div>
    </div>
  {:else if !error}
    <div class="glass-card p-6 text-center content-enter">
      <div class="text-4xl mb-3">📅</div>
      <h3 class="font-bold text-lg mb-2">No Matches Today</h3>
      <p class="text-slate-400 text-sm">Check back tomorrow for match predictions!</p>
    </div>
  {/if}

  <!-- Today's Other Matches -->
  {#if todaysMatches.length > 1}
    <div class="glass-card p-4 md:p-6 content-enter">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg md:text-xl font-bold">Today's Matches</h2>
        <span class="text-sm text-slate-400">{todaysMatches.length} matches</span>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 stagger-enter">
        {#each todaysMatches.slice(1, 7) as fixture}
          <Link
            to={`/prediction/${fixture.fixture.id}?league=${fixture.league?.id || 39}&season=${season}`}
            class="bg-white/5 rounded-lg p-3 card-interactive flex items-center justify-between gap-2"
          >
            <div class="flex items-center gap-2 flex-1 min-w-0">
              <img src={fixture.teams.home.logo} alt="" class="w-6 h-6 flex-shrink-0" />
              <span class="text-sm truncate">{fixture.teams.home.name}</span>
            </div>
            <span class="text-xs text-slate-500 font-mono px-2">{formatTime(fixture.fixture.date)}</span>
            <div class="flex items-center gap-2 flex-1 min-w-0 justify-end">
              <span class="text-sm truncate">{fixture.teams.away.name}</span>
              <img src={fixture.teams.away.logo} alt="" class="w-6 h-6 flex-shrink-0" />
            </div>
          </Link>
        {/each}
      </div>

      {#if todaysMatches.length > 7}
        <div class="mt-4 text-center">
          <Link
            to="/fixtures"
            class="inline-flex items-center gap-2 text-accent hover:text-accent/80 text-sm font-medium btn-press"
          >
            View all {todaysMatches.length} matches
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </Link>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Quick Access Grid -->
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6 stagger-enter">
    <Link
      to="/fixtures"
      class="glass-card p-5 md:p-6 card-interactive group touch-target"
    >
      <div
        class="w-10 h-10 md:w-12 md:h-12 rounded-lg bg-blue-500/20 flex items-center justify-center text-blue-400 mb-3 md:mb-4 icon-hover text-xl md:text-2xl"
      >
        📅
      </div>
      <h3 class="text-lg md:text-xl font-bold mb-2">Today's Fixtures</h3>
      <p class="text-xs md:text-sm text-slate-400">
        Browse matches playing today across 14 major leagues. Predictions are generated on match day.
      </p>
    </Link>

    <Link
      to="/teams"
      class="glass-card p-5 md:p-6 card-interactive group touch-target"
    >
      <div
        class="w-10 h-10 md:w-12 md:h-12 rounded-lg bg-emerald-500/20 flex items-center justify-center text-emerald-400 mb-3 md:mb-4 icon-hover text-xl md:text-2xl"
      >
        🛡️
      </div>
      <h3 class="text-lg md:text-xl font-bold mb-2">Team Stats</h3>
      <p class="text-xs md:text-sm text-slate-400">
        Analyze detailed team statistics, form guides, and performance metrics.
      </p>
    </Link>

    <Link
      to="/predictions"
      class="glass-card p-5 md:p-6 card-interactive group touch-target sm:col-span-2 lg:col-span-1"
    >
      <div
        class="w-10 h-10 md:w-12 md:h-12 rounded-lg bg-purple-500/20 flex items-center justify-center text-purple-400 mb-3 md:mb-4 icon-hover text-xl md:text-2xl"
      >
        🧠
      </div>
      <h3 class="text-lg md:text-xl font-bold mb-2">AI Models</h3>
      <p class="text-xs md:text-sm text-slate-400">
        Access predictions from our ensemble of 11 ML models including GBDT,
        LSTM, GNN, and Monte Carlo simulation.
      </p>
    </Link>
  </div>

  <!-- Additional Features Grid -->
  <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 md:gap-4 stagger-enter">
    <Link
      to="/standings"
      class="glass-card p-4 card-interactive text-center touch-target"
    >
      <div class="text-2xl md:text-3xl mb-1 md:mb-2">🏆</div>
      <h4 class="font-bold text-sm md:text-base">Standings</h4>
    </Link>

    <Link
      to="/results"
      class="glass-card p-4 card-interactive text-center touch-target"
    >
      <div class="text-2xl md:text-3xl mb-1 md:mb-2">📊</div>
      <h4 class="font-bold text-sm md:text-base">Results</h4>
    </Link>

    <Link
      to="/live"
      class="glass-card p-4 card-interactive text-center touch-target"
    >
      <div class="text-2xl md:text-3xl mb-1 md:mb-2">🔴</div>
      <h4 class="font-bold text-sm md:text-base">Live Scores</h4>
    </Link>

    <Link
      to="/models"
      class="glass-card p-4 card-interactive text-center touch-target"
    >
      <div class="text-2xl md:text-3xl mb-1 md:mb-2">📈</div>
      <h4 class="font-bold text-sm md:text-base">Model Stats</h4>
    </Link>
  </div>
</div>

<style>
  /* Page-specific animations handled by global CSS */
</style>
