<script>
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import { API_URL } from "../config.js";
  import SearchBar from "../components/SearchBar.svelte";
  import { getCurrentSeason } from "../services/season.js";
  import { getSavedLeague, saveLeague, getSavedSeason, saveSeason } from "../services/preferences.js";

  // All supported leagues
  const leagues = [
    // European Competitions (Tier 0)
    { id: 2, name: "Champions League", country: "Europe", emoji: "🏆", tier: 0 },
    { id: 3, name: "Europa League", country: "Europe", emoji: "🥈", tier: 0 },
    { id: 848, name: "Conference League", country: "Europe", emoji: "🥉", tier: 0 },
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
    // Domestic Cups (Tier 3)
    { id: 45, name: "FA Cup", country: "England", emoji: "🏆", tier: 3 },
    { id: 48, name: "League Cup", country: "England", emoji: "🏆", tier: 3 },
  ];

  let teams = [];
  let loading = true;
  let selectedLeague = getSavedLeague(39);
  let searchQuery = "";
  let season = getSavedSeason(getCurrentSeason());
  let showLeagueSelector = false;

  async function loadTeams(leagueId) {
    loading = true;
    selectedLeague = leagueId;
    saveLeague(leagueId);
    saveSeason(season);
    try {
      const res = await fetch(
        `${API_URL}/api/teams?league=${leagueId}&season=${season}`,
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

  $: filteredTeams = teams.filter((item) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const name = item.team.name.toLowerCase();
    const code = item.team.code ? item.team.code.toLowerCase() : "";
    return name.includes(q) || code.includes(q);
  });

  $: currentLeague = leagues.find(l => l.id === selectedLeague) || leagues.find(l => l.id === 39);

  function handleClickOutside(event) {
    if (showLeagueSelector && !event.target.closest('.league-selector')) {
      showLeagueSelector = false;
    }
  }
</script>

<svelte:window on:click={handleClickOutside} />

<div class="space-y-6 page-enter">
  <div class="flex flex-col gap-3 mb-2 element-enter">
    <div class="flex justify-between items-center gap-3">
      <h2 class="text-2xl font-bold">Teams</h2>

      <!-- League Selector Dropdown -->
      <div class="league-selector relative">
        <button
          class="league-selector-btn flex items-center gap-2 px-4 py-2 bg-white/10 rounded-lg hover:bg-white/15 transition-all"
          on:click|stopPropagation={() => showLeagueSelector = !showLeagueSelector}
        >
          <span class="text-lg">{currentLeague?.emoji}</span>
          <span class="font-medium">{currentLeague?.name}</span>
          <svg class="w-4 h-4 transition-transform {showLeagueSelector ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {#if showLeagueSelector}
          <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
          <div class="league-dropdown absolute right-0 top-full mt-2 w-64 max-h-80 overflow-y-auto bg-slate-900 border border-white/20 rounded-xl shadow-2xl z-50" on:click|stopPropagation>
            <!-- European -->
            <div class="p-2 border-b border-white/10">
              <div class="text-xs text-slate-400 px-2 py-1 font-bold">🏆 EUROPEAN</div>
              {#each leagues.filter(l => l.tier === 0) as league}
                <button
                  type="button"
                  class="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/10 transition-all {selectedLeague === league.id ? 'bg-accent/20 text-accent' : ''}"
                  on:click={() => { loadTeams(league.id); showLeagueSelector = false; }}
                >
                  <span>{league.emoji}</span>
                  <span>{league.name}</span>
                </button>
              {/each}
            </div>
            <!-- Top Leagues -->
            <div class="p-2 border-b border-white/10">
              <div class="text-xs text-slate-400 px-2 py-1 font-bold">⭐ TOP LEAGUES</div>
              {#each leagues.filter(l => l.tier === 1) as league}
                <button
                  type="button"
                  class="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/10 transition-all {selectedLeague === league.id ? 'bg-accent/20 text-accent' : ''}"
                  on:click={() => { loadTeams(league.id); showLeagueSelector = false; }}
                >
                  <span>{league.emoji}</span>
                  <span>{league.name}</span>
                </button>
              {/each}
            </div>
            <!-- Second Division -->
            <div class="p-2 border-b border-white/10">
              <div class="text-xs text-slate-400 px-2 py-1 font-bold">📋 SECOND DIVISION</div>
              {#each leagues.filter(l => l.tier === 2) as league}
                <button
                  type="button"
                  class="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/10 transition-all {selectedLeague === league.id ? 'bg-accent/20 text-accent' : ''}"
                  on:click={() => { loadTeams(league.id); showLeagueSelector = false; }}
                >
                  <span>{league.emoji}</span>
                  <span>{league.name}</span>
                </button>
              {/each}
            </div>
            <!-- Domestic Cups -->
            <div class="p-2">
              <div class="text-xs text-slate-400 px-2 py-1 font-bold">🏆 DOMESTIC CUPS</div>
              {#each leagues.filter(l => l.tier === 3) as league}
                <button
                  type="button"
                  class="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/10 transition-all {selectedLeague === league.id ? 'bg-orange-500/20 text-orange-400' : ''}"
                  on:click={() => { loadTeams(league.id); showLeagueSelector = false; }}
                >
                  <span>{league.emoji}</span>
                  <span>{league.name}</span>
                </button>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    </div>
    <SearchBar bind:searchQuery selectedLeague={selectedLeague} />
  </div>

  {#if loading}
    <div class="text-center py-20">Loading teams...</div>
  {:else}
    <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4 element-enter stagger-1">
      {#each filteredTeams as item}
        <Link
          to={`/team/${item.team.id}?league=${selectedLeague}`}
          class="glass-card p-4 flex flex-col items-center justify-center gap-4 hover:bg-white/5 team-card"
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
