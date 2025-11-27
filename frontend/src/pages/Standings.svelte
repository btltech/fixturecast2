<script>
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import { API_URL } from "../config.js";
  import { getCurrentSeason } from "../services/season.js";
  import { getSavedLeague, saveLeague, getSavedSeason, saveSeason } from "../services/preferences.js";

  let selectedLeague = getSavedLeague(39); // Premier League default (persisted)
  let standings = [];
  let loading = true;
  let error = null;
  let leagueInfo = null;
  const season = getSavedSeason(getCurrentSeason());

  const leagues = [
    { id: 39, name: "Premier League", country: "England", flag: "🏴󠁧󠁢󠁥󠁮󠁧󠁿" },
    { id: 140, name: "La Liga", country: "Spain", flag: "🇪🇸" },
    { id: 135, name: "Serie A", country: "Italy", flag: "🇮🇹" },
    { id: 78, name: "Bundesliga", country: "Germany", flag: "🇩🇪" },
    { id: 61, name: "Ligue 1", country: "France", flag: "🇫🇷" },
    { id: 88, name: "Eredivisie", country: "Netherlands", flag: "🇳🇱" },
    { id: 94, name: "Primeira Liga", country: "Portugal", flag: "🇵🇹" },
    { id: 40, name: "Championship", country: "England", flag: "🏴󠁧󠁢󠁥󠁮󠁧󠁿" },
    { id: 141, name: "Segunda División", country: "Spain", flag: "🇪🇸" },
    { id: 2, name: "Champions League", country: "UEFA", flag: "🇪🇺" },
    { id: 3, name: "Europa League", country: "UEFA", flag: "🇪🇺" },
  ];

  async function fetchStandings() {
    loading = true;
    error = null;
    try {
      const response = await fetch(
        `${API_URL}/api/standings?league=${selectedLeague}&season=${season}`
      );
      if (!response.ok) throw new Error("Failed to fetch standings");
      const data = await response.json();

      if (data.response && data.response[0]) {
        leagueInfo = data.response[0].league;
        standings = data.response[0].league.standings[0] || [];
      }
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    saveSeason(season);
    fetchStandings();
  });

  function getFormColor(result) {
    if (result === "W") return "bg-green-500";
    if (result === "D") return "bg-yellow-500";
    if (result === "L") return "bg-red-500";
    return "bg-gray-500";
  }

  function getPositionColor(rank) {
    if (rank <= 4) return "text-green-400"; // Champions League
    if (rank <= 6) return "text-blue-400"; // Europa League
    if (rank >= standings.length - 2) return "text-red-400"; // Relegation
    return "text-slate-300";
  }
</script>

<div class="space-y-6 page-enter">
  <!-- Header -->
  <div class="glass-card p-6 element-enter">
    <h1 class="text-3xl font-bold mb-4">League Standings</h1>

    <!-- League Selector -->
    <div class="flex flex-wrap gap-2">
      {#each leagues as league}
        <button
          on:click={() => {
            selectedLeague = league.id;
            saveLeague(selectedLeague);
            fetchStandings();
          }}
          class="px-4 py-2 rounded-lg btn-interact {selectedLeague ===
          league.id
            ? 'bg-accent text-white'
            : 'bg-white/5 hover:bg-white/10'}"
        >
          <span class="mr-2">{league.flag}</span>
          {league.name}
        </button>
      {/each}
    </div>
  </div>

  {#if loading}
    <div class="glass-card p-12 text-center">
      <div
        class="inline-block w-12 h-12 border-4 border-accent border-t-transparent rounded-full animate-spin"
      ></div>
      <p class="mt-4 text-slate-400">Loading standings...</p>
    </div>
  {:else if error}
    <div class="glass-card p-8 text-center border border-red-500/30">
      <p class="text-red-400">❌ {error}</p>
    </div>
  {:else if standings.length > 0}
    <!-- Standings Table -->
    <div class="glass-card overflow-hidden element-enter stagger-1">
      <!-- League Info -->
      {#if leagueInfo}
        <div class="p-4 border-b border-white/10 flex items-center gap-3">
          <img
            src={leagueInfo.logo}
            alt={leagueInfo.name}
            class="w-12 h-12"
          />
          <div>
            <h2 class="text-xl font-bold">{leagueInfo.name}</h2>
            <p class="text-sm text-slate-400">
              {leagueInfo.country} • Season {leagueInfo.season}
            </p>
          </div>
        </div>
      {/if}

      <!-- Table -->
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="bg-white/5 border-b border-white/10">
            <tr class="text-left text-sm">
              <th class="p-3 w-16">#</th>
              <th class="p-3">Team</th>
              <th class="p-3 text-center w-16">P</th>
              <th class="p-3 text-center w-16">W</th>
              <th class="p-3 text-center w-16">D</th>
              <th class="p-3 text-center w-16">L</th>
              <th class="p-3 text-center w-20">GF</th>
              <th class="p-3 text-center w-20">GA</th>
              <th class="p-3 text-center w-20">GD</th>
              <th class="p-3 text-center w-20 font-bold">Pts</th>
              <th class="p-3">Form</th>
            </tr>
          </thead>
          <tbody>
            {#each standings as team, i}
              <tr
                class="border-b border-white/5 hover:bg-white/5 transition-colors"
              >
                <td class="p-3">
                  <span class={getPositionColor(team.rank) + " font-bold"}>
                    {team.rank}
                  </span>
                </td>
                <td class="p-3">
                  <Link
                    to="/team/{team.team.id}?league={selectedLeague}&season={season}"
                    class="flex items-center gap-2 hover:text-accent transition-colors"
                  >
                    <img
                      src={team.team.logo}
                      alt={team.team.name}
                      class="w-6 h-6"
                    />
                    <span class="font-medium">{team.team.name}</span>
                  </Link>
                </td>
                <td class="p-3 text-center text-slate-400">{team.all.played}</td>
                <td class="p-3 text-center text-green-400">{team.all.win}</td>
                <td class="p-3 text-center text-yellow-400">{team.all.draw}</td>
                <td class="p-3 text-center text-red-400">{team.all.lose}</td>
                <td class="p-3 text-center">{team.all.goals.for}</td>
                <td class="p-3 text-center">{team.all.goals.against}</td>
                <td
                  class="p-3 text-center {team.goalsDiff >= 0
                    ? 'text-green-400'
                    : 'text-red-400'}"
                >
                  {team.goalsDiff > 0 ? "+" : ""}{team.goalsDiff}
                </td>
                <td class="p-3 text-center text-lg font-bold text-accent">
                  {team.points}
                </td>
                <td class="p-3">
                  <div class="flex gap-0.5">
                    {#if team.form}
                      {#each team.form.split("").slice(-5) as result}
                        <div
                          class="{getFormColor(
                            result
                          )} w-6 h-6 rounded flex items-center justify-center text-xs font-bold"
                          title={result === "W"
                            ? "Win"
                            : result === "D"
                              ? "Draw"
                              : "Loss"}
                        >
                          {result}
                        </div>
                      {/each}
                    {/if}
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Legend -->
      <div class="p-4 bg-white/5 border-t border-white/10 text-xs space-y-2">
        <div class="flex flex-wrap gap-4">
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 bg-green-500 rounded"></div>
            <span class="text-slate-400">Champions League</span>
          </div>
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 bg-blue-500 rounded"></div>
            <span class="text-slate-400">Europa League</span>
          </div>
          <div class="flex items-center gap-2">
            <div class="w-3 h-3 bg-red-500 rounded"></div>
            <span class="text-slate-400">Relegation</span>
          </div>
        </div>
        <div class="text-slate-500">
          P=Played, W=Won, D=Draw, L=Lost, GF=Goals For, GA=Goals Against,
          GD=Goal Difference, Pts=Points
        </div>
      </div>
    </div>
  {:else}
    <div class="glass-card p-8 text-center">
      <p class="text-slate-400">No standings available</p>
    </div>
  {/if}
</div>
