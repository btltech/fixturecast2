<script>
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";

  let teams = [];
  let loading = true;
  let selectedLeague = 39;

  async function loadTeams(leagueId) {
    loading = true;
    selectedLeague = leagueId;
    try {
      const res = await fetch(
        `http://localhost:8001/api/teams?league=${leagueId}&season=2025`,
      );
      const data = await res.json();
      // Force Svelte reactivity by creating a new array reference
      teams = [...(data.response || [])];
    } catch (e) {
      console.error("Error loading teams:", e);
      teams = [];
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    loadTeams(39);
  });
</script>

<div class="space-y-6">
  <div class="flex justify-between items-center">
    <h2 class="text-2xl font-bold">Teams</h2>
    <select
      class="bg-secondary text-white border border-white/10 rounded-md px-4 py-2"
      on:change={(e) => loadTeams(parseInt(e.currentTarget.value, 10))}
    >
      <option value="39">Premier League</option>
      <option value="140">La Liga</option>
      <option value="135">Serie A</option>
      <option value="78">Bundesliga</option>
      <option value="61">Ligue 1</option>
    </select>
  </div>

  {#if loading}
    <div class="text-center py-20">Loading teams...</div>
  {:else}
    <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
      {#each teams as item}
        <Link
          to={`/team/${item.team.id}`}
          class="glass-card p-4 flex flex-col items-center justify-center gap-4 hover:bg-white/5 transition-all hover:-translate-y-1"
        >
          <img
            src={item.team.logo}
            alt={item.team.name}
            class="w-20 h-20 object-contain"
          />
          <span class="font-bold text-center">{item.team.name}</span>
          <span class="text-xs text-slate-500">{item.venue.name}</span>
        </Link>
      {/each}
    </div>
  {/if}
</div>
