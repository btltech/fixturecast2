<script>
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import { API_URL } from "../config.js";

  export let id;

  let team = null;
  let stats = null;
  let fixtures = [];
  let upcoming = [];
  let injuries = [];
  let currentInjuries = [];
  let standings = null;
  let loading = true;
  let error = null;
  let league = 39; // Default to Premier League

  onMount(async () => {
    try {
      // Get league from URL params if provided
      const urlParams = new URLSearchParams(window.location.search);
      const leagueParam = urlParams.get("league");
      league = leagueParam ? parseInt(leagueParam, 10) : 39;

      // Fetch Stats
      const statsRes = await fetch(
        `${API_URL}/api/team/${id}/stats?league=${league}&season=2025`,
      );
      const statsData = await statsRes.json();

      if (statsData.response) {
        team = statsData.response;
        stats = statsData.response;
      }

      // Fetch Standings to get league position
      const standingsRes = await fetch(
        `${API_URL}/api/standings?league=${league}&season=2025`,
      );
      const standingsData = await standingsRes.json();
      
      if (standingsData.response && standingsData.response[0]) {
        const leagueStandings = standingsData.response[0].league.standings[0];
        standings = leagueStandings.find(s => s.team.id == id);
      }

      // Fetch Recent Fixtures (last 5 games)
      const fixturesRes = await fetch(
        `${API_URL}/api/team/${id}/fixtures?league=${league}&season=2025&last=5`,
      );
      const fixturesData = await fixturesRes.json();

      if (fixturesData.response) {
        fixtures = fixturesData.response;
      }

      // Fetch Upcoming Matches (next 2 games)
      const upcomingRes = await fetch(
        `${API_URL}/api/team/${id}/upcoming?league=${league}&season=2025&next=2`,
      );
      const upcomingData = await upcomingRes.json();

      if (upcomingData.response) {
        upcoming = upcomingData.response;
      }

      // Fetch Injuries
      const injuriesRes = await fetch(
        `${API_URL}/api/team/${id}/injuries?season=2025`,
      );
      const injuriesData = await injuriesRes.json();

      if (injuriesData.response) {
        injuries = injuriesData.response;
        // Filter to only show current injuries (where fixture date is in the future or undefined)
        const now = new Date();
        currentInjuries = injuries.filter(injury => {
          if (!injury.fixture || !injury.fixture.date) {
            // If no fixture date, assume it's current
            return true;
          }
          const fixtureDate = new Date(injury.fixture.date);
          return fixtureDate >= now;
        });
      }

      loading = false;
    } catch (e) {
      error = e.message;
      loading = false;
    }
  });
</script>

{#if loading}
  <div class="text-center py-20">
    <div
      class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-accent"
    ></div>
    <p class="mt-4 text-slate-400">Loading team details...</p>
  </div>
{:else if team}
  <div class="max-w-6xl mx-auto space-y-8 page-enter">
    <!-- Header -->
    <div class="glass-card p-8 element-enter">
      <div class="flex flex-col md:flex-row items-center gap-8">
        <img
          src={team.team.logo}
          alt={team.team.name}
          class="w-32 h-32 object-contain"
        />
        <div class="text-center md:text-left flex-1">
          <h1
            class="text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400 mb-2"
          >
            {team.team.name}
          </h1>
          <div
            class="flex flex-wrap gap-4 text-slate-400 justify-center md:justify-start mt-4"
          >
            {#if team.venue?.name}
              <span class="flex items-center gap-2">
                <span class="text-accent">🏟️</span>
                {team.venue.name}
                {#if team.venue?.capacity}
                  <span class="text-xs opacity-60">({team.venue.capacity.toLocaleString()} capacity)</span>
                {/if}
              </span>
            {/if}
            {#if team.team?.founded}
              <span>•</span>
              <span class="flex items-center gap-2">
                <span class="text-accent">📅</span>
                Founded {team.team.founded}
              </span>
            {/if}
            {#if team.venue?.city}
              <span>•</span>
              <span class="flex items-center gap-2">
                <span class="text-accent">📍</span>
                {team.venue.city}, {team.team.country}
              </span>
            {/if}
          </div>
        </div>
        {#if standings}
          <div class="glass-card p-6 text-center bg-gradient-to-br from-accent/10 to-blue-500/10 border-accent/30">
            <div class="text-sm text-slate-400 mb-2">League Position</div>
            <div class="text-5xl font-bold text-accent mb-2">{standings.rank}</div>
            <div class="text-2xl font-semibold text-white">{standings.points} pts</div>
            {#if standings.form}
              <div class="text-xs text-slate-400 mt-3">
                Recent Form: <span class="font-mono font-bold">{standings.form}</span>
              </div>
            {/if}
          </div>
        {/if}
      </div>
    </div>

    <!-- Additional Club Info -->
    {#if stats}
      <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 element-enter stagger-1">
        <!-- Win Rate -->
        <div class="glass-card p-4 text-center">
          <div class="text-3xl font-bold text-emerald-400 mb-1">
            {stats.fixtures?.played?.total ? ((stats.fixtures.wins.total / stats.fixtures.played.total) * 100).toFixed(0) : 0}%
          </div>
          <div class="text-slate-400 text-xs">Win Rate</div>
        </div>

        <!-- Clean Sheets -->
        <div class="glass-card p-4 text-center">
          <div class="text-3xl font-bold text-blue-400 mb-1">
            {stats.clean_sheet?.total || 0}
          </div>
          <div class="text-slate-400 text-xs">Clean Sheets</div>
        </div>

        <!-- Failed to Score -->
        <div class="glass-card p-4 text-center">
          <div class="text-3xl font-bold text-rose-400 mb-1">
            {stats.failed_to_score?.total || 0}
          </div>
          <div class="text-slate-400 text-xs">Failed to Score</div>
        </div>

        <!-- Penalty Scored -->
        <div class="glass-card p-4 text-center">
          <div class="text-3xl font-bold text-purple-400 mb-1">
            {stats.penalty?.scored?.total || 0}
          </div>
          <div class="text-slate-400 text-xs">Penalties Scored</div>
        </div>

        <!-- Yellow Cards -->
        <div class="glass-card p-4 text-center">
          <div class="text-3xl font-bold text-amber-400 mb-1">
            {(stats.cards?.yellow?.['0-15']?.total || 0) + (stats.cards?.yellow?.['16-30']?.total || 0) + (stats.cards?.yellow?.['31-45']?.total || 0) + (stats.cards?.yellow?.['46-60']?.total || 0) + (stats.cards?.yellow?.['61-75']?.total || 0) + (stats.cards?.yellow?.['76-90']?.total || 0)}
          </div>
          <div class="text-slate-400 text-xs">Yellow Cards</div>
        </div>

        <!-- Red Cards -->
        <div class="glass-card p-4 text-center">
          <div class="text-3xl font-bold text-red-500 mb-1">
            {(stats.cards?.red?.['0-15']?.total || 0) + (stats.cards?.red?.['16-30']?.total || 0) + (stats.cards?.red?.['31-45']?.total || 0) + (stats.cards?.red?.['46-60']?.total || 0) + (stats.cards?.red?.['61-75']?.total || 0) + (stats.cards?.red?.['76-90']?.total || 0)}
          </div>
          <div class="text-slate-400 text-xs">Red Cards</div>
        </div>
      </div>

      <!-- Home vs Away Performance -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6 element-enter stagger-2">
        <div class="glass-card p-6">
          <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
            <span class="text-2xl">🏠</span>
            Home Record
          </h3>
          <div class="space-y-3">
            <div class="flex justify-between items-center">
              <span class="text-slate-400">Played</span>
              <span class="text-xl font-bold text-white">
                {stats.fixtures?.played?.home || 0}
              </span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-slate-400">Wins</span>
              <span class="text-xl font-bold text-emerald-400">
                {stats.fixtures?.wins?.home || 0}
              </span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-slate-400">Draws</span>
              <span class="text-xl font-bold text-amber-400">
                {stats.fixtures?.draws?.home || 0}
              </span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-slate-400">Losses</span>
              <span class="text-xl font-bold text-rose-400">
                {stats.fixtures?.loses?.home || 0}
              </span>
            </div>
            <div class="pt-3 border-t border-white/10">
              <div class="flex justify-between items-center">
                <span class="text-slate-400">Goals For</span>
                <span class="text-lg font-semibold text-emerald-400">
                  {stats.goals?.for?.total?.home || 0}
                </span>
              </div>
              <div class="flex justify-between items-center mt-2">
                <span class="text-slate-400">Goals Against</span>
                <span class="text-lg font-semibold text-rose-400">
                  {stats.goals?.against?.total?.home || 0}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div class="glass-card p-6">
          <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
            <span class="text-2xl">✈️</span>
            Away Record
          </h3>
          <div class="space-y-3">
            <div class="flex justify-between items-center">
              <span class="text-slate-400">Played</span>
              <span class="text-xl font-bold text-white">
                {stats.fixtures?.played?.away || 0}
              </span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-slate-400">Wins</span>
              <span class="text-xl font-bold text-emerald-400">
                {stats.fixtures?.wins?.away || 0}
              </span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-slate-400">Draws</span>
              <span class="text-xl font-bold text-amber-400">
                {stats.fixtures?.draws?.away || 0}
              </span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-slate-400">Losses</span>
              <span class="text-xl font-bold text-rose-400">
                {stats.fixtures?.loses?.away || 0}
              </span>
            </div>
            <div class="pt-3 border-t border-white/10">
              <div class="flex justify-between items-center">
                <span class="text-slate-400">Goals For</span>
                <span class="text-lg font-semibold text-emerald-400">
                  {stats.goals?.for?.total?.away || 0}
                </span>
              </div>
              <div class="flex justify-between items-center mt-2">
                <span class="text-slate-400">Goals Against</span>
                <span class="text-lg font-semibold text-rose-400">
                  {stats.goals?.against?.total?.away || 0}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Scoring Statistics -->
      <div class="glass-card p-6">
        <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
          <span class="w-1 h-6 bg-gradient-to-b from-emerald-400 to-rose-400 rounded-full"></span>
          Goal Timing Analysis
        </h3>
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {#each [
            { label: '0-15', key: '0-15' },
            { label: '16-30', key: '16-30' },
            { label: '31-45', key: '31-45' },
            { label: '46-60', key: '46-60' },
            { label: '61-75', key: '61-75' },
            { label: '76-90', key: '76-90' }
          ] as period}
            <div class="text-center p-3 rounded-lg bg-white/5">
              <div class="text-xs text-slate-400 mb-2">{period.label} min</div>
              <div class="flex justify-around">
                <div class="flex flex-col items-center">
                  <div class="text-sm font-bold text-emerald-400">
                    {stats.goals?.for?.minute?.[period.key]?.total || 0}
                  </div>
                  <div class="text-xs text-slate-500">For</div>
                </div>
                <div class="flex flex-col items-center">
                  <div class="text-sm font-bold text-rose-400">
                    {stats.goals?.against?.minute?.[period.key]?.total || 0}
                  </div>
                  <div class="text-xs text-slate-500">Agst</div>
                </div>
              </div>
            </div>
          {/each}
        </div>
      </div>

      <!-- Biggest Wins/Losses -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="glass-card p-6 text-center bg-gradient-to-br from-emerald-500/10 to-emerald-500/5">
          <div class="text-sm text-slate-400 mb-2">Biggest Win</div>
          <div class="text-3xl font-bold text-emerald-400 mb-1">
            {stats.biggest?.wins?.home || stats.biggest?.wins?.away || 'N/A'}
          </div>
          <div class="text-xs text-slate-500">
            {stats.biggest?.wins?.home ? 'Home' : stats.biggest?.wins?.away ? 'Away' : ''}
          </div>
        </div>

        <div class="glass-card p-6 text-center bg-gradient-to-br from-rose-500/10 to-rose-500/5">
          <div class="text-sm text-slate-400 mb-2">Biggest Loss</div>
          <div class="text-3xl font-bold text-rose-400 mb-1">
            {stats.biggest?.loses?.home || stats.biggest?.loses?.away || 'N/A'}
          </div>
          <div class="text-xs text-slate-500">
            {stats.biggest?.loses?.home ? 'Home' : stats.biggest?.loses?.away ? 'Away' : ''}
          </div>
        </div>

        <div class="glass-card p-6 text-center bg-gradient-to-br from-accent/10 to-blue-500/5">
          <div class="text-sm text-slate-400 mb-2">Goal Difference</div>
          <div class="text-3xl font-bold text-accent mb-1">
            {(stats.goals?.for?.total?.total || 0) - (stats.goals?.against?.total?.total || 0) >= 0 ? '+' : ''}{(stats.goals?.for?.total?.total || 0) - (stats.goals?.against?.total?.total || 0)}
          </div>
          <div class="text-xs text-slate-500">Overall</div>
        </div>
      </div>
    {/if}

    <!-- Statistics -->
    {#if stats}
      <div class="glass-card p-6">
        <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
          <span class="w-1 h-6 bg-accent rounded-full"></span>
          Season Overview
        </h3>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-6">
          <!-- Matches Played -->
          <div class="text-center">
            <div class="text-4xl font-bold text-accent mb-2">
              {stats.fixtures?.played?.total || 0}
            </div>
            <div class="text-slate-400 text-sm">Matches Played</div>
          </div>

          <!-- Wins -->
          <div class="text-center">
            <div class="text-4xl font-bold text-emerald-400 mb-2">
              {stats.fixtures?.wins?.total || 0}
            </div>
            <div class="text-slate-400 text-sm">Wins</div>
          </div>

          <!-- Draws -->
          <div class="text-center">
            <div class="text-4xl font-bold text-amber-400 mb-2">
              {stats.fixtures?.draws?.total || 0}
            </div>
            <div class="text-slate-400 text-sm">Draws</div>
          </div>

          <!-- Losses -->
          <div class="text-center">
            <div class="text-4xl font-bold text-rose-400 mb-2">
              {stats.fixtures?.loses?.total || 0}
            </div>
            <div class="text-slate-400 text-sm">Losses</div>
          </div>
        </div>
      </div>

      <!-- Goals Stats -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="glass-card p-6">
          <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
            <span class="w-1 h-6 bg-emerald-400 rounded-full"></span>
            Goals Scored
          </h3>
          <div class="space-y-3">
            <div class="flex justify-between items-center">
              <span class="text-slate-400">Total</span>
              <span class="text-2xl font-bold text-emerald-400">
                {stats.goals?.for?.total?.total || 0}
              </span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-slate-400">Average per Match</span>
              <span class="text-lg font-semibold">
                {stats.goals?.for?.average?.total || "0.0"}
              </span>
            </div>
            <div class="flex justify-between items-center pt-2 border-t border-white/10">
              <span class="text-slate-400 text-sm">Home</span>
              <span class="font-semibold text-emerald-300">
                {stats.goals?.for?.total?.home || 0}
              </span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-slate-400 text-sm">Away</span>
              <span class="font-semibold text-emerald-300">
                {stats.goals?.for?.total?.away || 0}
              </span>
            </div>
          </div>
        </div>

        <div class="glass-card p-6">
          <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
            <span class="w-1 h-6 bg-rose-400 rounded-full"></span>
            Goals Conceded
          </h3>
          <div class="space-y-3">
            <div class="flex justify-between items-center">
              <span class="text-slate-400">Total</span>
              <span class="text-2xl font-bold text-rose-400">
                {stats.goals?.against?.total?.total || 0}
              </span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-slate-400">Average per Match</span>
              <span class="text-lg font-semibold">
                {stats.goals?.against?.average?.total || "0.0"}
              </span>
            </div>
            <div class="flex justify-between items-center pt-2 border-t border-white/10">
              <span class="text-slate-400 text-sm">Home</span>
              <span class="font-semibold text-rose-300">
                {stats.goals?.against?.total?.home || 0}
              </span>
            </div>
            <div class="flex justify-between items-center">
              <span class="text-slate-400 text-sm">Away</span>
              <span class="font-semibold text-rose-300">
                {stats.goals?.against?.total?.away || 0}
              </span>
            </div>
          </div>
        </div>
      </div>
    {/if}

    <!-- Upcoming Matches -->
    {#if upcoming.length > 0}
      <div class="glass-card p-6">
        <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
          <span class="w-1 h-6 bg-blue-400 rounded-full"></span>
          Upcoming Matches
        </h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          {#each upcoming as match}
            <Link
              to={`/prediction/${match.fixture.id}`}
              class="p-4 rounded-lg bg-white/5 hover:bg-white/10 transition-all border border-white/10 hover:border-accent/30 flex flex-col items-center text-center group"
            >
              <div class="text-xs text-slate-400 mb-2">
                {new Date(match.fixture.date).toLocaleDateString()}
              </div>
              <div class="flex items-center justify-between w-full mb-2">
                <img
                  src={match.teams.home.logo}
                  alt={match.teams.home.name}
                  class="w-8 h-8 object-contain"
                />
                <span class="text-sm font-bold text-slate-500">VS</span>
                <img
                  src={match.teams.away.logo}
                  alt={match.teams.away.name}
                  class="w-8 h-8 object-contain"
                />
              </div>
              <div
                class="text-sm font-semibold group-hover:text-accent transition-colors"
              >
                {match.teams.home.name} vs {match.teams.away.name}
              </div>
              <div
                class="mt-2 text-xs px-2 py-1 rounded-full bg-accent/20 text-accent"
              >
                View Prediction
              </div>
            </Link>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Injuries -->
    {#if currentInjuries.length > 0}
      <div class="glass-card p-6">
        <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
          <span class="w-1 h-6 bg-rose-400 rounded-full"></span>
          Current Injuries & Team News
        </h3>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {#each currentInjuries as injury}
            <div
              class="flex items-start gap-4 p-4 rounded-lg bg-white/5 border border-white/10"
            >
              <img
                src={injury.player.photo}
                alt={injury.player.name}
                class="w-10 h-10 rounded-full object-cover"
              />
              <div>
                <div class="font-bold text-white">{injury.player.name}</div>
                <div class="text-sm text-rose-400">{injury.player.reason}</div>
                {#if injury.player.type}
                  <div class="text-xs text-slate-500 mt-1">
                    Type: {injury.player.type}
                  </div>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      </div>
    {:else if injuries.length > 0}
      <div class="glass-card p-6 text-center">
        <h3 class="text-xl font-bold mb-2 flex items-center justify-center gap-2">
          <span class="text-emerald-400">✓</span>
          No Current Injuries
        </h3>
        <p class="text-slate-400 text-sm">All players are available for selection</p>
      </div>
    {/if}

    <!-- Recent Form (Last 5 + Next 2) -->
    {#if fixtures.length > 0 || upcoming.length > 0}
      <div class="glass-card p-6">
        <h3 class="text-xl font-bold mb-4 flex items-center gap-2">
          <span class="w-1 h-6 bg-accent rounded-full"></span>
          Recent Form (Last 5 Games + Next 2 Fixtures)
        </h3>
        <div class="space-y-3">
          <!-- Past matches -->
          {#each fixtures as fixture}
            {#if fixture.goals.home !== null}
              {@const isHome = fixture.teams.home.id == id}
              {@const goalsFor = isHome
                ? fixture.goals.home
                : fixture.goals.away}
              {@const goalsAgainst = isHome
                ? fixture.goals.away
                : fixture.goals.home}
              {@const result =
                goalsFor > goalsAgainst
                  ? "W"
                  : goalsFor === goalsAgainst
                    ? "D"
                    : "L"}
              {@const resultColor =
                result === "W"
                  ? "text-emerald-400 bg-emerald-400/10 border-emerald-400/20"
                  : result === "D"
                    ? "text-amber-400 bg-amber-400/10 border-amber-400/20"
                    : "text-rose-400 bg-rose-400/10 border-rose-400/20"}

              <Link
                to={`/prediction/${fixture.fixture.id}`}
                class="flex items-center gap-4 p-4 rounded-lg hover:bg-white/5 transition-all border border-white/10 hover:border-accent/30"
              >
                <div
                  class={`w-12 h-12 rounded-lg flex items-center justify-center font-bold text-lg border ${resultColor}`}
                >
                  {result}
                </div>
                <div class="flex-1">
                  <div class="font-semibold mb-1">
                    {fixture.teams.home.name} vs {fixture.teams.away.name}
                  </div>
                  <div class="text-sm text-slate-400">
                    {new Date(fixture.fixture.date).toLocaleDateString()} • Score:
                    {fixture.goals.home} - {fixture.goals.away}
                  </div>
                </div>
                <div class="text-2xl font-bold">
                  {goalsFor} - {goalsAgainst}
                </div>
              </Link>
            {/if}
          {/each}

          <!-- Divider if we have both past and upcoming -->
          {#if fixtures.length > 0 && upcoming.length > 0}
            <div class="flex items-center gap-4 my-4">
              <div class="flex-1 h-px bg-gradient-to-r from-transparent via-accent/30 to-transparent"></div>
              <span class="text-xs text-accent font-semibold uppercase tracking-wider">Upcoming Fixtures</span>
              <div class="flex-1 h-px bg-gradient-to-r from-transparent via-accent/30 to-transparent"></div>
            </div>
          {/if}

          <!-- Upcoming matches -->
          {#each upcoming as match}
            {@const isHome = match.teams.home.id == id}
            <Link
              to={`/prediction/${match.fixture.id}`}
              class="flex items-center gap-4 p-4 rounded-lg hover:bg-white/5 transition-all border border-blue-500/30 hover:border-accent/50 bg-blue-500/5"
            >
              <div
                class="w-12 h-12 rounded-lg flex items-center justify-center font-bold text-lg border border-blue-400/30 bg-blue-400/10 text-blue-400"
              >
                VS
              </div>
              <div class="flex-1">
                <div class="font-semibold mb-1 flex items-center gap-2">
                  {match.teams.home.name} vs {match.teams.away.name}
                  <span class="text-xs px-2 py-1 rounded-full bg-blue-400/20 text-blue-400">Next</span>
                </div>
                <div class="text-sm text-slate-400">
                  {new Date(match.fixture.date).toLocaleDateString()} • {new Date(match.fixture.date).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'})}
                </div>
              </div>
              <div class="flex items-center gap-2">
                <img
                  src={isHome ? match.teams.away.logo : match.teams.home.logo}
                  alt={isHome ? match.teams.away.name : match.teams.home.name}
                  class="w-8 h-8 object-contain"
                />
              </div>
            </Link>
          {/each}
        </div>
      </div>
    {/if}
  </div>
{:else}
  <div class="text-center py-20">
    <p class="text-slate-400 text-lg">Team not found</p>
  </div>
{/if}
