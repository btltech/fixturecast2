<script>
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import { API_URL } from "../config.js";
  import { getCurrentSeason } from "../services/season.js";
  import { getSavedLeague, saveLeague } from "../services/preferences.js";

  let selectedLeague = getSavedLeague(39);
  let results = [];
  let loading = true;
  let error = null;
  const season = getCurrentSeason();

  const leagues = [
    // European Competitions
    { id: 2, name: "Champions League", flag: "🏆", tier: 0 },
    { id: 3, name: "Europa League", flag: "🥈", tier: 0 },
    { id: 848, name: "Conference League", flag: "🥉", tier: 0 },
    // Top Leagues
    { id: 39, name: "Premier League", flag: "🏴󠁧󠁢󠁥󠁮󠁧󠁿", tier: 1 },
    { id: 140, name: "La Liga", flag: "🇪🇸", tier: 1 },
    { id: 135, name: "Serie A", flag: "🇮🇹", tier: 1 },
    { id: 78, name: "Bundesliga", flag: "🇩🇪", tier: 1 },
    { id: 61, name: "Ligue 1", flag: "🇫🇷", tier: 1 },
    { id: 88, name: "Eredivisie", flag: "🇳🇱", tier: 1 },
    { id: 94, name: "Primeira Liga", flag: "🇵🇹", tier: 1 },
    // Second Division
    { id: 40, name: "Championship", flag: "🏴󠁧󠁢󠁥󠁮󠁧󠁿", tier: 2 },
    { id: 141, name: "Segunda División", flag: "🇪🇸", tier: 2 },
    { id: 136, name: "Serie B", flag: "🇮🇹", tier: 2 },
    { id: 79, name: "2. Bundesliga", flag: "🇩🇪", tier: 2 },
    { id: 62, name: "Ligue 2", flag: "🇫🇷", tier: 2 },
    // Domestic Cups
    { id: 45, name: "FA Cup", flag: "🏆", tier: 3 },
    { id: 48, name: "League Cup", flag: "🏆", tier: 3 },
  ];

  async function fetchResults() {
    loading = true;
    error = null;
    try {
      const response = await fetch(
        `${API_URL}/api/results?league=${selectedLeague}&last=20&season=${season}`
      );
      if (!response.ok) throw new Error("Failed to fetch results");
      const data = await response.json();
      results = data.response || [];
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    fetchResults();
  });

  function changeLeague(leagueId) {
    selectedLeague = leagueId;
    saveLeague(leagueId);
    fetchResults();
  }

  function getResultBadge(homeScore, awayScore) {
    if (homeScore > awayScore) return { text: "W", color: "bg-green-500" };
    if (homeScore < awayScore) return { text: "L", color: "bg-red-500" };
    return { text: "D", color: "bg-yellow-500" };
  }
</script>

<div class="space-y-6 page-enter">
  <div class="glass-card p-6 element-enter">
    <h1 class="text-3xl font-bold mb-4">Recent Results</h1>

    <!-- European Competitions -->
    <div class="mb-3">
      <div class="text-xs text-slate-400 mb-2 font-bold">🏆 EUROPEAN</div>
      <div class="flex flex-wrap gap-2">
        {#each leagues.filter(l => l.tier === 0) as league}
          <button
            on:click={() => changeLeague(league.id)}
            class="px-3 py-1.5 rounded-lg text-sm btn-interact {selectedLeague === league.id ? 'bg-accent text-white' : 'bg-white/5 hover:bg-white/10'}"
          >
            <span class="mr-1">{league.flag}</span>
            {league.name}
          </button>
        {/each}
      </div>
    </div>

    <!-- Top Leagues -->
    <div class="mb-3">
      <div class="text-xs text-slate-400 mb-2 font-bold">⭐ TOP LEAGUES</div>
      <div class="flex flex-wrap gap-2">
        {#each leagues.filter(l => l.tier === 1) as league}
          <button
            on:click={() => changeLeague(league.id)}
            class="px-3 py-1.5 rounded-lg text-sm btn-interact {selectedLeague === league.id ? 'bg-accent text-white' : 'bg-white/5 hover:bg-white/10'}"
          >
            <span class="mr-1">{league.flag}</span>
            {league.name}
          </button>
        {/each}
      </div>
    </div>

    <!-- Second Division -->
    <div class="mb-3">
      <div class="text-xs text-slate-400 mb-2 font-bold">📋 SECOND DIVISION</div>
      <div class="flex flex-wrap gap-2">
        {#each leagues.filter(l => l.tier === 2) as league}
          <button
            on:click={() => changeLeague(league.id)}
            class="px-3 py-1.5 rounded-lg text-sm btn-interact {selectedLeague === league.id ? 'bg-accent text-white' : 'bg-white/5 hover:bg-white/10'}"
          >
            <span class="mr-1">{league.flag}</span>
            {league.name}
          </button>
        {/each}
      </div>
    </div>

    <!-- Domestic Cups -->
    <div>
      <div class="text-xs text-slate-400 mb-2 font-bold">🏆 DOMESTIC CUPS</div>
      <div class="flex flex-wrap gap-2">
        {#each leagues.filter(l => l.tier === 3) as league}
          <button
            on:click={() => changeLeague(league.id)}
            class="px-3 py-1.5 rounded-lg text-sm btn-interact {selectedLeague === league.id ? 'bg-orange-500/80 text-white' : 'bg-white/5 hover:bg-white/10'}"
          >
            <span class="mr-1">{league.flag}</span>
            {league.name}
          </button>
        {/each}
      </div>
    </div>
  </div>

  {#if loading}
    <div class="glass-card p-12 text-center">
      <div
        class="inline-block w-12 h-12 border-4 border-accent border-t-transparent rounded-full animate-spin"
      ></div>
      <p class="mt-4 text-slate-400">Loading results...</p>
    </div>
  {:else if error}
    <div class="glass-card p-8 text-center border border-red-500/30">
      <p class="text-red-400">❌ {error}</p>
    </div>
  {:else if results.length > 0}
    <div class="space-y-4 element-enter stagger-1">
      {#each results as match}
        <div class="glass-card p-6 hover:bg-white/5 result-card">
          <div class="flex items-center justify-between mb-4">
            <div class="text-sm text-slate-400">
              {new Date(match.fixture.date).toLocaleDateString("en-US", {
                weekday: "short",
                month: "short",
                day: "numeric",
                year: "numeric",
              })}
            </div>
            <div class="text-xs px-2 py-1 rounded bg-slate-700">
              {match.league.round}
            </div>
          </div>

          <div class="grid grid-cols-[1fr_auto_1fr] gap-4 items-center">
            <Link
              to="/team/{match.teams.home.id}?league={match.league.id}"
              class="flex items-center gap-3 justify-end hover:text-accent transition-colors"
            >
              <span class="text-lg font-bold text-right"
                >{match.teams.home.name}</span
              >
              <img
                src={match.teams.home.logo}
                alt={match.teams.home.name}
                class="w-12 h-12"
              />
            </Link>

            <div class="flex items-center gap-3">
              <div
                class="text-3xl font-bold px-4 py-2 bg-white/10 rounded-lg min-w-[80px] text-center"
              >
                {match.goals.home} - {match.goals.away}
              </div>
            </div>

            <Link
              to="/team/{match.teams.away.id}?league={match.league.id}"
              class="flex items-center gap-3 hover:text-accent transition-colors"
            >
              <img
                src={match.teams.away.logo}
                alt={match.teams.away.name}
                class="w-12 h-12"
              />
              <span class="text-lg font-bold">{match.teams.away.name}</span>
            </Link>
          </div>

          {#if match.fixture.venue?.name}
            <div class="mt-4 text-sm text-slate-400 text-center">
              📍 {match.fixture.venue.name}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {:else}
    <div class="glass-card p-8 text-center">
      <p class="text-slate-400">No results available</p>
    </div>
  {/if}
</div>
