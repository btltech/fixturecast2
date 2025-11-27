<script>
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import { API_URL, ML_API_URL } from "../config.js";
  import SkeletonLoader from "../components/SkeletonLoader.svelte";
  import SearchBar from "../components/SearchBar.svelte";
  import ConfidenceBadge from "../components/ConfidenceBadge.svelte";
  import AccuracyTracker from "../components/AccuracyTracker.svelte";
  import { compareStore } from "../services/compareStore.js";
  import { getCurrentSeason } from "../services/season.js";
  import { getSavedLeague, saveLeague, getSavedSeason, saveSeason } from "../services/preferences.js";

  // Use reactive auto-subscription ($ prefix) - automatically unsubscribes
  $: compareFixtures = $compareStore?.fixtures || [];
  $: compareLeagues = $compareStore?.fixtureLeagues || {};

  function toggleCompare(fixtureId) {
    compareStore.addFixture(fixtureId, selectedLeague);
  }

  function isInCompare(fixtureId) {
    return compareFixtures.includes(fixtureId);
  }

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
    // Domestic Cups (Tier 3)
    { id: 45, name: "FA Cup", country: "England", emoji: "🏆", tier: 3 },
    { id: 48, name: "League Cup", country: "England", emoji: "🏆", tier: 3 },
  ];

  // Create league map for quick lookup
  const leaguesMap = {};
  leagues.forEach(l => leaguesMap[l.id] = l);

  let selectedLeague = getSavedLeague(39); // Default: Premier League (persisted)
  let season = getSavedSeason(getCurrentSeason());
  let fixtures = [];
  let deduplicatedFixtures = [];
  let loading = false;
  let showLeagueSelector = false;
  let fixturesRequestToken = 0;

  // Predictions state - on demand
  let predictions = {}; // fixture_id -> prediction data
  let loadingPredictions = {}; // fixture_id -> boolean
  let predictionRequestTokens = {}; // fixture_id -> request token
  let searchQuery = "";

  // UK timezone helpers
  function getUKDate() {
    const now = new Date();
    const ukTime = new Date(now.toLocaleString("en-US", { timeZone: "Europe/London" }));
    return ukTime;
  }

  function formatUKDate(date) {
    return new Date(date).toLocaleDateString("en-GB", {
      timeZone: "Europe/London",
      weekday: "short",
      day: "numeric",
      month: "short"
    });
  }

  function formatUKTime(date) {
    return new Date(date).toLocaleTimeString("en-GB", {
      timeZone: "Europe/London",
      hour: "2-digit",
      minute: "2-digit"
    });
  }

  function getUKMidnightInfo() {
    const ukNow = getUKDate();
    const hours = ukNow.getHours();
    const mins = ukNow.getMinutes();
    return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')} UK`;
  }

  $: currentLeague = leaguesMap[selectedLeague] || leagues[0];
  $: ukTimeNow = getUKMidnightInfo();

  // Deduplicate fixtures - one game per team
  function deduplicateFixtures(fixtureList) {
    const seenTeams = new Set();
    const result = [];

    const sorted = [...fixtureList].sort((a, b) =>
      new Date(a.fixture.date).getTime() - new Date(b.fixture.date).getTime()
    );

    for (const fixture of sorted) {
      const homeId = fixture.teams.home.id;
      const awayId = fixture.teams.away.id;

      if (!seenTeams.has(homeId) && !seenTeams.has(awayId)) {
        result.push(fixture);
        seenTeams.add(homeId);
        seenTeams.add(awayId);
      }
    }

    return result;
  }

  async function loadFixtures() {
    loading = true;
    saveSeason(season);
    fixtures = [];
    deduplicatedFixtures = [];
    predictions = {};
    const requestId = ++fixturesRequestToken;

    try {
      const res = await fetch(
        `${API_URL}/api/fixtures?league=${selectedLeague}&season=${season}&next=40`
      );
      const data = await res.json();

      if (
        requestId === fixturesRequestToken &&
        data.response &&
        Array.isArray(data.response)
      ) {
        fixtures = data.response.filter(f =>
          f.fixture.status?.short === 'NS' || f.fixture.status?.short === 'TBD'
        );

        deduplicatedFixtures = deduplicateFixtures(fixtures);
      }
    } catch (e) {
      if (requestId === fixturesRequestToken) {
        console.error("Error loading fixtures:", e);
      }
    } finally {
      if (requestId === fixturesRequestToken) {
        loading = false;
      }
    }
  }

  async function changeLeague(leagueId) {
    selectedLeague = leagueId;
    saveLeague(leagueId);
    showLeagueSelector = false;
    await loadFixtures();
  }

  async function loadPrediction(fixtureId) {
    if (predictions[fixtureId] || loadingPredictions[fixtureId]) {
      return;
    }

    loadingPredictions[fixtureId] = true;
    loadingPredictions = {...loadingPredictions};
    const requestId = (predictionRequestTokens[fixtureId] || 0) + 1;
    predictionRequestTokens[fixtureId] = requestId;
    predictionRequestTokens = {...predictionRequestTokens};

    try {
      const res = await fetch(
        `${ML_API_URL}/api/prediction/${fixtureId}?league=${selectedLeague}&season=${season}`
      );

      if (res.ok) {
        const data = await res.json();
        if (predictionRequestTokens[fixtureId] === requestId) {
          predictions[fixtureId] = data.prediction;
          predictions = {...predictions};
        }
      }
    } catch (e) {
      console.error(`Error loading prediction for ${fixtureId}:`, e);
    } finally {
      if (predictionRequestTokens[fixtureId] === requestId) {
        loadingPredictions[fixtureId] = false;
        loadingPredictions = {...loadingPredictions};
      }
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

  $: filteredFixtures = deduplicatedFixtures.filter((fixture) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const home = fixture.teams.home.name.toLowerCase();
    const away = fixture.teams.away.name.toLowerCase();
    return home.includes(q) || away.includes(q);
  });

  function handleClickOutside(event) {
    if (showLeagueSelector && !event.target.closest('.league-selector')) {
      showLeagueSelector = false;
    }
  }

  onMount(() => {
    loadFixtures();
  });
</script>

<svelte:window on:click={handleClickOutside} />

<div class="page-enter flex flex-col lg:flex-row gap-4 lg:gap-8">
  <!-- Mobile League Selector Button -->
  <div class="lg:hidden league-selector element-enter">
    <button
      on:click={() => showLeagueSelector = !showLeagueSelector}
      class="w-full glass-card p-4 flex items-center justify-between touch-target btn-interact"
    >
      <div class="flex items-center gap-3">
        <span class="text-xl">{currentLeague.emoji}</span>
        <div>
          <div class="font-bold">{currentLeague.name}</div>
          <div class="text-xs text-slate-400">One game per team • UK Time</div>
        </div>
      </div>
      <svg
        class="w-5 h-5 text-slate-400 transition-transform {showLeagueSelector ? 'rotate-180' : ''}"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <!-- Mobile League Dropdown -->
    {#if showLeagueSelector}
      <div class="glass-card mt-2 p-2 max-h-80 overflow-y-auto">
        <!-- European Competitions -->
        <div class="text-xs text-slate-400 px-2 py-1 font-bold">EUROPEAN COMPETITIONS</div>
        {#each leagues.filter(l => l.tier === 0) as league}
          <button
            class="w-full text-left px-3 py-3 rounded-lg text-sm transition-colors flex items-center gap-3 touch-target {selectedLeague === league.id
              ? 'bg-accent text-white font-bold'
              : 'text-slate-300 hover:bg-white/10'}"
            on:click={() => changeLeague(league.id)}
          >
            <span>{league.emoji}</span>
            <span class="flex-1">{league.name}</span>
          </button>
        {/each}

        <div class="text-xs text-slate-400 px-2 py-1 font-bold mt-3">TOP LEAGUES</div>
        {#each leagues.filter(l => l.tier === 1) as league}
          <button
            class="w-full text-left px-3 py-3 rounded-lg text-sm transition-colors flex items-center gap-3 touch-target {selectedLeague === league.id
              ? 'bg-accent text-white font-bold'
              : 'text-slate-300 hover:bg-white/10'}"
            on:click={() => changeLeague(league.id)}
          >
            <span>{league.emoji}</span>
            <span class="flex-1">{league.name}</span>
          </button>
        {/each}

        <div class="text-xs text-slate-400 px-2 py-1 font-bold mt-3">SECOND DIVISIONS</div>
        {#each leagues.filter(l => l.tier === 2) as league}
          <button
            class="w-full text-left px-3 py-3 rounded-lg text-sm transition-colors flex items-center gap-3 touch-target {selectedLeague === league.id
              ? 'bg-accent text-white font-bold'
              : 'text-slate-300 hover:bg-white/10'}"
            on:click={() => changeLeague(league.id)}
          >
            <span>{league.emoji}</span>
            <span class="flex-1">{league.name}</span>
          </button>
        {/each}

        <div class="text-xs text-slate-400 px-2 py-1 font-bold mt-3">DOMESTIC CUPS</div>
        {#each leagues.filter(l => l.tier === 3) as league}
          <button
            class="w-full text-left px-3 py-3 rounded-lg text-sm transition-colors flex items-center gap-3 touch-target {selectedLeague === league.id
              ? 'bg-accent text-white font-bold'
              : 'text-slate-300 hover:bg-white/10'}"
            on:click={() => changeLeague(league.id)}
          >
            <span>{league.emoji}</span>
            <span class="flex-1">{league.name}</span>
          </button>
        {/each}
      </div>
    {/if}
  </div>

  <!-- Desktop Sidebar -->
  <aside class="hidden lg:block w-64 flex-shrink-0 league-selector element-enter stagger-1">
    <div class="glass-card p-4 sticky top-24">
      <h3 class="text-lg font-bold mb-4 text-slate-300">Select League</h3>
      <p class="text-xs text-slate-500 mb-4">🕐 Current UK Time: {ukTimeNow}</p>

      <div class="space-y-4">
        <!-- European Competitions -->
        <div>
          <div class="text-xs font-semibold text-yellow-400 uppercase tracking-wider mb-2 px-3">
            European
          </div>
          <div class="space-y-1">
            {#each leagues.filter(l => l.tier === 0) as league}
              <button
                class="w-full text-left px-3 py-2 rounded-md text-sm transition-colors {selectedLeague === league.id
                  ? 'bg-accent text-primary font-bold'
                  : 'text-slate-400 hover:bg-white/5 hover:text-white'}"
                on:click={() => changeLeague(league.id)}
              >
                <div class="flex justify-between items-center">
                  <span>{league.name}</span>
                  <span class="text-xs opacity-60">{league.emoji}</span>
                </div>
              </button>
            {/each}
          </div>
        </div>

        <!-- Top Leagues -->
        <div>
          <div class="text-xs font-semibold text-accent uppercase tracking-wider mb-2 px-3 pt-2 border-t border-white/10">
            Top Leagues
          </div>
          <div class="space-y-1">
            {#each leagues.filter(l => l.tier === 1) as league}
              <button
                class="w-full text-left px-3 py-2 rounded-md text-sm transition-colors {selectedLeague === league.id
                  ? 'bg-accent text-primary font-bold'
                  : 'text-slate-400 hover:bg-white/5 hover:text-white'}"
                on:click={() => changeLeague(league.id)}
              >
                <div class="flex justify-between items-center">
                  <span>{league.name}</span>
                  <span class="text-xs opacity-60">{league.emoji}</span>
                </div>
              </button>
            {/each}
          </div>
        </div>

        <!-- Second Divisions -->
        <div>
          <div class="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2 px-3 pt-2 border-t border-white/10">
            Second Divisions
          </div>
          <div class="space-y-1">
            {#each leagues.filter(l => l.tier === 2) as league}
              <button
                class="w-full text-left px-3 py-2 rounded-md text-sm transition-colors {selectedLeague === league.id
                  ? 'bg-accent text-primary font-bold'
                  : 'text-slate-400 hover:bg-white/5 hover:text-white'}"
                on:click={() => changeLeague(league.id)}
              >
                <div class="flex justify-between items-center">
                  <span>{league.name}</span>
                  <span class="text-xs opacity-60">{league.emoji}</span>
                </div>
              </button>
            {/each}
          </div>
        </div>

        <!-- Domestic Cups -->
        <div>
          <div class="text-xs font-semibold text-orange-400 uppercase tracking-wider mb-2 px-3 pt-2 border-t border-white/10">
            Domestic Cups
          </div>
          <div class="space-y-1">
            {#each leagues.filter(l => l.tier === 3) as league}
              <button
                class="w-full text-left px-3 py-2 rounded-md text-sm transition-colors {selectedLeague === league.id
                  ? 'bg-accent text-primary font-bold'
                  : 'text-slate-400 hover:bg-white/5 hover:text-white'}"
                on:click={() => changeLeague(league.id)}
              >
                <div class="flex justify-between items-center">
                  <span>{league.name}</span>
                  <span class="text-xs opacity-60">{league.emoji}</span>
                </div>
              </button>
            {/each}
          </div>
        </div>
      </div>
    </div>
  </aside>

  <!-- Main Content -->
  <div class="flex-grow element-enter stagger-2">
    <div class="flex flex-col gap-3 mb-4 lg:mb-6">
      <div class="flex items-center justify-between gap-3">
        <div>
          <h2 class="text-xl lg:text-2xl font-bold">{currentLeague.emoji} {currentLeague.name} Fixtures</h2>
          <p class="text-sm text-slate-400">One game per team • Predictions on demand</p>
        </div>
        <button
          on:click={loadFixtures}
          class="p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
          title="Refresh fixtures"
        >
          <svg class="w-5 h-5 {loading ? 'animate-spin' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
      <SearchBar bind:searchQuery selectedLeague={selectedLeague} />
    </div>

    <!-- Info Banner -->
    <div class="bg-accent/10 border border-accent/30 rounded-lg p-3 mb-4 text-sm">
      <div class="flex items-start gap-2">
        <span class="text-accent">🎯</span>
        <p class="text-slate-300">
          <strong class="text-white">Smart Fixtures:</strong> Showing one upcoming game per team. Click "Get AI Prediction" to load analysis on demand.
        </p>
      </div>
    </div>

    <!-- Accuracy Tracker -->
    <div class="mb-4">
      <AccuracyTracker league={selectedLeague} compact={true} />
    </div>

    {#if loading}
      <!-- Skeleton Loading -->
      <div class="grid gap-4 md:grid-cols-2">
        {#each Array(6) as _}
          <SkeletonLoader type="fixture" />
        {/each}
      </div>
    {:else if filteredFixtures.length > 0}
      <!-- Fixtures Grid -->
      <div class="grid gap-4 md:grid-cols-2">
        {#each filteredFixtures as fixture (fixture.fixture.id)}
          {@const fixtureId = fixture.fixture.id}
          {@const pred = predictions[fixtureId]}
          {@const summary = getPredictionSummary(pred)}

          <div class="glass-card p-4 relative overflow-hidden group fixture-card">
            <!-- Compare Button (top right) -->
            <button
              on:click|stopPropagation={() => toggleCompare(fixtureId)}
              class="absolute top-2 right-2 p-1.5 rounded-lg transition-all z-10 {isInCompare(fixtureId) ? 'bg-accent text-white' : 'bg-white/10 text-slate-400 opacity-0 group-hover:opacity-100 hover:bg-white/20'}"
              title={isInCompare(fixtureId) ? 'Remove from compare' : 'Add to compare'}
            >
              ⚖️
            </button>

            <!-- Match Time Header -->
            <div class="flex items-center justify-between mb-3 pr-8">
              <span class="text-xs text-slate-400">
                {formatUKDate(fixture.fixture.date)}
              </span>
              <span class="text-sm text-accent font-mono font-bold">
                {formatUKTime(fixture.fixture.date)} UK
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
                <div class="font-medium text-sm truncate px-1">{fixture.teams.home.name}</div>
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
                <div class="font-medium text-sm truncate px-1">{fixture.teams.away.name}</div>
              </div>
            </div>

            <!-- Prediction Section -->
            {#if pred}
              <!-- Show prediction result with confidence badge -->
              <div class="bg-gradient-to-r from-accent/10 to-purple-500/10 rounded-lg p-3 border border-accent/20">
                <div class="flex justify-between items-center mb-2">
                  <span class="text-xs text-slate-400">AI Prediction</span>
                  <ConfidenceBadge confidence={summary.prob / 100} size="sm" showLabel={false} />
                </div>
                <div class="flex justify-between items-center text-xs mb-2">
                  <span class="font-medium {summary.winner === 'home' ? 'text-emerald-400' : summary.winner === 'away' ? 'text-rose-400' : 'text-slate-300'}">{summary.label}</span>
                  <span class="text-accent font-bold">{summary.prob.toFixed(0)}%</span>
                </div>
                <div class="flex gap-1 h-2 rounded-full overflow-hidden bg-slate-700">
                  <div
                    class="bg-green-500 transition-all"
                    style="width: {pred.home_win_prob * 100}%"
                    title="Home: {(pred.home_win_prob * 100).toFixed(1)}%"
                  ></div>
                  <div
                    class="bg-slate-400 transition-all"
                    style="width: {pred.draw_prob * 100}%"
                    title="Draw: {(pred.draw_prob * 100).toFixed(1)}%"
                  ></div>
                  <div
                    class="bg-red-500 transition-all"
                    style="width: {pred.away_win_prob * 100}%"
                    title="Away: {(pred.away_win_prob * 100).toFixed(1)}%"
                  ></div>
                </div>
                <div class="flex justify-between text-xs mt-1 text-slate-500">
                  <span>H: {(pred.home_win_prob * 100).toFixed(0)}%</span>
                  <span>D: {(pred.draw_prob * 100).toFixed(0)}%</span>
                  <span>A: {(pred.away_win_prob * 100).toFixed(0)}%</span>
                </div>
                <Link to={`/prediction/${fixtureId}?league=${selectedLeague}&season=${season}`} class="view-analysis-btn">
                  <span>🔮</span>
                  <span>View Full Analysis</span>
                  <svg class="arrow-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M5 12h14M12 5l7 7-7 7"/>
                  </svg>
                </Link>
              </div>
            {:else}
              <!-- Show get prediction button -->
              <button
                on:click={() => loadPrediction(fixtureId)}
                disabled={loadingPredictions[fixtureId]}
                class="w-full py-3 bg-accent/20 hover:bg-accent/30 text-accent rounded-lg font-medium text-sm flex items-center justify-center gap-2 disabled:opacity-50 btn-interact"
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

      <!-- Summary -->
      <div class="mt-4 text-center text-sm text-slate-500">
        <p>Showing {deduplicatedFixtures.length} fixtures (one per team)</p>
        {#if fixtures.length > deduplicatedFixtures.length}
          <p class="text-xs text-slate-600 mt-1">
            {fixtures.length - deduplicatedFixtures.length} additional fixtures filtered out
          </p>
        {/if}
      </div>
    {:else}
      <div class="text-center py-12 text-slate-500 glass-card">
        <div class="text-4xl mb-4">📅</div>
        <p class="font-medium text-lg mb-2">No upcoming fixtures</p>
        <p class="text-sm text-slate-400">
          There are no upcoming {currentLeague.name} fixtures scheduled.
        </p>
        <p class="text-xs text-slate-500 mt-4">
          Try selecting a different league or check back later!
        </p>
      </div>
    {/if}
  </div>
</div>

<style>
    :global(.view-analysis-btn) {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        margin-top: 12px;
        padding: 10px 16px;
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.2), rgba(236, 72, 153, 0.15));
        border: 1px solid rgba(139, 92, 246, 0.4);
        border-radius: 10px;
        color: #c4b5fd;
        font-size: 0.875rem;
        font-weight: 600;
        text-decoration: none;
        transition: all 0.2s ease;
        cursor: pointer;
    }

    :global(.view-analysis-btn:hover) {
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.35), rgba(236, 72, 153, 0.25));
        border-color: rgba(139, 92, 246, 0.6);
        transform: translateY(-2px);
        box-shadow: 0 4px 20px rgba(139, 92, 246, 0.25);
    }

    :global(.view-analysis-btn:active) {
        transform: translateY(0) scale(0.98);
    }

    :global(.view-analysis-btn .arrow-icon) {
        transition: transform 0.2s ease;
    }

    :global(.view-analysis-btn:hover .arrow-icon) {
        transform: translateX(3px);
    }
</style>
