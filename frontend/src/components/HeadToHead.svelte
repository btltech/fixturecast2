<script>
  import { Link } from "svelte-routing";

  export let homeTeam;
  export let awayTeam;

  let h2hData = null;
  let loading = true;
  let error = null;

  async function fetchH2H() {
    loading = true;
    error = null;
    try {
      const response = await fetch(
        `http://localhost:8001/api/h2h/${homeTeam.id}/${awayTeam.id}`
      );
      if (!response.ok) throw new Error("Failed to fetch H2H data");
      const data = await response.json();
      h2hData = data;
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  $: if (homeTeam && awayTeam) {
    fetchH2H();
  }

  function getResultForTeam(match, teamId) {
    const homeScore = match.goals.home;
    const awayScore = match.goals.away;
    const isHome = match.teams.home.id === teamId;

    if (homeScore === awayScore) return { text: "D", color: "bg-yellow-500" };
    if ((isHome && homeScore > awayScore) || (!isHome && awayScore > homeScore)) {
      return { text: "W", color: "bg-green-500" };
    }
    return { text: "L", color: "bg-red-500" };
  }
</script>

<div class="glass-card p-6">
  <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
    <span>⚔️</span>
    <span>Head-to-Head</span>
  </h3>

  {#if loading}
    <div class="text-center py-8">
      <div
        class="inline-block w-8 h-8 border-4 border-accent border-t-transparent rounded-full animate-spin"
      ></div>
      <p class="mt-2 text-sm text-slate-400">Loading H2H data...</p>
    </div>
  {:else if error}
    <div class="text-center py-4 text-red-400 text-sm">❌ {error}</div>
  {:else if h2hData}
    <!-- Summary Stats -->
    <div class="grid grid-cols-3 gap-4 mb-6">
      <div class="text-center">
        <div class="text-2xl font-bold text-green-400">{h2hData.home_wins}</div>
        <div class="text-xs text-slate-400">{homeTeam.name} Wins</div>
      </div>
      <div class="text-center">
        <div class="text-2xl font-bold text-yellow-400">{h2hData.draws}</div>
        <div class="text-xs text-slate-400">Draws</div>
      </div>
      <div class="text-center">
        <div class="text-2xl font-bold text-red-400">{h2hData.away_wins}</div>
        <div class="text-xs text-slate-400">{awayTeam.name} Wins</div>
      </div>
    </div>

    <!-- Recent Meetings -->
    {#if h2hData.recent_matches && h2hData.recent_matches.length > 0}
      <div class="space-y-2">
        <div class="text-sm font-bold text-slate-400 mb-2">
          Last {h2hData.recent_matches.length} Meetings
        </div>
        {#each h2hData.recent_matches as match}
          <div
            class="bg-white/5 rounded-lg p-3 flex items-center justify-between"
          >
            <div class="flex items-center gap-2 flex-1">
              <img
                src={match.teams.home.logo}
                alt={match.teams.home.name}
                class="w-6 h-6"
              />
              <span class="text-sm">{match.teams.home.name}</span>
            </div>
            <div class="flex items-center gap-2 font-bold">
              <span>{match.goals?.home ?? '-'}</span>
              <span class="text-slate-500">-</span>
              <span>{match.goals?.away ?? '-'}</span>
            </div>
            <div class="flex items-center gap-2 flex-1 justify-end">
              <span class="text-sm">{match.teams.away.name}</span>
              <img
                src={match.teams.away.logo}
                alt={match.teams.away.name}
                class="w-6 h-6"
              />
            </div>
            <div class="ml-4 text-xs text-slate-400">
              {new Date(match.fixture.date).toLocaleDateString("en-US", {
                month: "short",
                year: "numeric",
              })}
            </div>
          </div>
        {/each}
      </div>
    {:else}
      <div class="text-center py-4 text-slate-400 text-sm">
        No recent meetings found
      </div>
    {/if}
  {/if}
</div>
