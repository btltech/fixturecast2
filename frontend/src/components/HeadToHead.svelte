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
        `http://localhost:8001/api/h2h/${homeTeam.id}/${awayTeam.id}`,
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
    if (
      (isHome && homeScore > awayScore) ||
      (!isHome && awayScore > homeScore)
    ) {
      return { text: "W", color: "bg-green-500" };
    }
    return { text: "L", color: "bg-red-500" };
  }
</script>

<div class="glass-card p-6 element-enter">
  <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
    <span>⚔️</span>
    <span>Head-to-Head</span>
  </h3>

  {#if loading}
    <div class="text-center py-8">
      <div
        class="inline-block w-8 h-8 border-4 border-accent border-t-transparent rounded-full loading-spin"
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
            class="bg-white/5 rounded-lg p-3 grid grid-cols-[1fr_auto_1fr] gap-2 items-center"
          >
            <!-- Home Team -->
            <div class="flex items-center gap-2 min-w-0">
              <img
                src={match.teams.home.logo}
                alt={match.teams.home.name}
                class="w-6 h-6 flex-shrink-0"
              />
              <span class="text-sm truncate" title={match.teams.home.name}>
                {match.teams.home.name}
              </span>
            </div>

            <!-- Score & Date -->
            <div class="flex flex-col items-center justify-center px-2">
              <div class="flex items-center gap-2 font-bold whitespace-nowrap">
                <span>{match.goals?.home ?? "-"}</span>
                <span class="text-slate-500">-</span>
                <span>{match.goals?.away ?? "-"}</span>
              </div>
              <div class="text-[10px] text-slate-500 whitespace-nowrap">
                {new Date(match.fixture.date).toLocaleDateString("en-US", {
                  month: "short",
                  year: "2-digit",
                })}
              </div>
            </div>

            <!-- Away Team -->
            <div class="flex items-center gap-2 justify-end min-w-0">
              <span
                class="text-sm truncate text-right"
                title={match.teams.away.name}
              >
                {match.teams.away.name}
              </span>
              <img
                src={match.teams.away.logo}
                alt={match.teams.away.name}
                class="w-6 h-6 flex-shrink-0"
              />
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
