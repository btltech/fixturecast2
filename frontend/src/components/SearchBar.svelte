<script>
  import { Link } from "svelte-routing";
  import { onMount } from "svelte";
  import { API_URL } from "../config.js";

  export let searchQuery = "";
  export let selectedLeague = 39; // Default to Premier League, but can be overridden
  
  let teams = [];
  let filteredTeams = [];
  let fixtures = [];
  let filteredFixtures = [];
  let showResults = false;
  let loading = false;
  let currentLeague = selectedLeague;

  async function loadData(leagueId) {
    try {
      const [teamsRes, fixturesRes] = await Promise.all([
        fetch(`${API_URL}/api/teams?league=${leagueId}&season=2025`),
        fetch(`${API_URL}/api/fixtures?league=${leagueId}&next=50&season=2025`),
      ]);
      const teamsData = await teamsRes.json();
      const fixturesData = await fixturesRes.json();

      teams = teamsData.response || [];
      fixtures = fixturesData.response || [];
    } catch (err) {
      console.error("Failed to load search data:", err);
    }
  }

  // Reload data when selectedLeague changes
  $: if (selectedLeague !== currentLeague) {
    currentLeague = selectedLeague;
    loadData(selectedLeague);
  }

  onMount(() => {
    loadData(selectedLeague);
  });

  function handleSearch() {
    if (!searchQuery.trim()) {
      showResults = false;
      return;
    }

    const query = searchQuery.toLowerCase();
    
    filteredTeams = teams.filter(
      (t) =>
        t.team.name.toLowerCase().includes(query) ||
        t.team.code?.toLowerCase().includes(query)
    ).slice(0, 5);

    filteredFixtures = fixtures.filter(
      (f) =>
        f.teams.home.name.toLowerCase().includes(query) ||
        f.teams.away.name.toLowerCase().includes(query)
    ).slice(0, 5);

    showResults = true;
  }

  function clearSearch() {
    searchQuery = "";
    showResults = false;
  }
</script>

<div class="relative">
  <div class="relative">
    <input
      type="text"
      bind:value={searchQuery}
      on:input={handleSearch}
      on:focus={handleSearch}
      placeholder="Search teams or fixtures..."
      class="w-full px-4 py-3 pl-12 bg-white/10 rounded-lg focus:bg-white/15 focus:outline-none focus:ring-2 focus:ring-accent search-input"
    />
    <div class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
      🔍
    </div>
    {#if searchQuery}
      <button
        on:click={clearSearch}
        class="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white btn-press"
      >
        ✕
      </button>
    {/if}
  </div>

  {#if showResults}
    <div
      class="absolute top-full mt-2 w-full bg-slate-900 border border-white/20 rounded-lg shadow-2xl max-h-96 overflow-y-auto z-50 search-results"
    >
      {#if filteredTeams.length === 0 && filteredFixtures.length === 0}
        <div class="p-4 text-center text-slate-400">No results found</div>
      {:else}
        <!-- Teams -->
        {#if filteredTeams.length > 0}
          <div class="p-2 border-b border-white/10">
            <div class="text-xs text-slate-400 px-2 py-1 font-bold">TEAMS</div>
            {#each filteredTeams as team}
              <Link
                to="/team/{team.team.id}?league={selectedLeague}"
                on:click={clearSearch}
                class="flex items-center gap-3 px-3 py-2 hover:bg-white/10 rounded-lg search-item"
              >
                <img
                  src={team.team.logo}
                  alt={team.team.name}
                  class="w-8 h-8"
                />
                <div>
                  <div class="font-medium">{team.team.name}</div>
                  {#if team.team.country}
                    <div class="text-xs text-slate-400">{team.team.country}</div>
                  {/if}
                </div>
              </Link>
            {/each}
          </div>
        {/if}

        <!-- Fixtures -->
        {#if filteredFixtures.length > 0}
          <div class="p-2">
            <div class="text-xs text-slate-400 px-2 py-1 font-bold">
              FIXTURES
            </div>
            {#each filteredFixtures as fixture}
              <Link
                to="/prediction/{fixture.fixture.id}"
                on:click={clearSearch}
                class="block px-3 py-2 hover:bg-white/10 rounded-lg search-item"
              >
                <div class="flex items-center justify-between gap-4">
                  <div class="flex items-center gap-2 flex-1">
                    <img
                      src={fixture.teams.home.logo}
                      alt={fixture.teams.home.name}
                      class="w-6 h-6"
                    />
                    <span class="text-sm">{fixture.teams.home.name}</span>
                  </div>
                  <span class="text-xs text-slate-400">vs</span>
                  <div class="flex items-center gap-2 flex-1 justify-end">
                    <span class="text-sm">{fixture.teams.away.name}</span>
                    <img
                      src={fixture.teams.away.logo}
                      alt={fixture.teams.away.name}
                      class="w-6 h-6"
                    />
                  </div>
                </div>
                <div class="text-xs text-slate-400 mt-1">
                  {new Date(fixture.fixture.date).toLocaleDateString()}
                </div>
              </Link>
            {/each}
          </div>
        {/if}
      {/if}
    </div>
  {/if}
</div>
