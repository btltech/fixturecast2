<script>
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";

  let liveMatches = [];
  let loading = true;
  let error = null;
  let refreshInterval;

  async function fetchLiveScores() {
    try {
      const response = await fetch("http://localhost:8001/api/live");
      if (!response.ok) throw new Error("Failed to fetch live scores");
      const data = await response.json();
      liveMatches = data.response || [];
      error = null;
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    fetchLiveScores();
    // Refresh every 30 seconds
    refreshInterval = setInterval(fetchLiveScores, 30000);
    return () => clearInterval(refreshInterval);
  });

  function getMinute(fixture) {
    return fixture.fixture.status.elapsed || "0";
  }
</script>

<div class="space-y-6 page-enter">
  <div class="glass-card p-6 element-enter">
    <div class="flex justify-between items-center">
      <div>
        <h1 class="text-3xl font-bold mb-2 flex items-center gap-2">
          <span class="relative flex h-3 w-3">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
          </span>
          Live Scores
        </h1>
        <p class="text-slate-400">Real-time match updates • Auto-refresh every 30s</p>
      </div>
      <button
        on:click={fetchLiveScores}
        class="px-4 py-2 bg-accent/20 text-accent rounded-lg hover:bg-accent/30 flex items-center gap-2 btn-interact"
      >
        <span>🔄</span>
        <span>Refresh</span>
      </button>
    </div>
  </div>

  {#if loading}
    <div class="glass-card p-12 text-center">
      <div
        class="inline-block w-12 h-12 border-4 border-accent border-t-transparent rounded-full animate-spin"
      ></div>
      <p class="mt-4 text-slate-400">Loading live matches...</p>
    </div>
  {:else if error}
    <div class="glass-card p-8 text-center border border-red-500/30">
      <p class="text-red-400">❌ {error}</p>
    </div>
  {:else if liveMatches.length === 0}
    <div class="glass-card p-12 text-center">
      <div class="text-6xl mb-4">⚽</div>
      <p class="text-xl font-bold mb-2">No Live Matches</p>
      <p class="text-slate-400">
        Check back later for live match updates
      </p>
    </div>
  {:else}
    <div class="space-y-4 element-enter stagger-1">
      {#each liveMatches as match}
        <div class="glass-card p-6 border-l-4 border-red-500 live-match-card">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
              <span class="relative flex h-2 w-2">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
              </span>
              <span class="text-red-400 font-bold">{getMinute(match)}'</span>
            </div>
            <div class="text-sm text-slate-400">{match.league.name}</div>
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

            <div class="text-center">
              <div
                class="text-4xl font-bold px-6 py-3 bg-white/10 rounded-lg min-w-[100px]"
              >
                {match.goals?.home ?? 0} - {match.goals?.away ?? 0}
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

          {#if match.events && match.events.length > 0}
            <div class="mt-4 text-sm text-slate-400">
              Recent: {match.events[0].detail}
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>
