<script>
  import { Link } from "svelte-routing";
  import { onMount } from "svelte";
  import { API_URL } from "../config.js";
  import { getCurrentSeason } from "../services/season.js";
  import { getSavedSeason, saveSeason } from "../services/preferences.js";
  import MatchCardSkeleton from "../components/MatchCardSkeleton.svelte";

  let matchOfTheDay = null;
  let todaysMatches = [];
  let loading = true;
  let error = null;
  const season = getSavedSeason(getCurrentSeason());

  // League info for display
  const leagueInfo = {
    39: { name: "Premier League", emoji: "🏴󠁧󠁢󠁥󠁮󠁧󠁿" },
    140: { name: "La Liga", emoji: "🇪🇸" },
    135: { name: "Serie A", emoji: "🇮🇹" },
    78: { name: "Bundesliga", emoji: "🇩🇪" },
    61: { name: "Ligue 1", emoji: "🇫🇷" },
    88: { name: "Eredivisie", emoji: "🇳🇱" },
    94: { name: "Primeira Liga", emoji: "🇵🇹" },
    2: { name: "Champions League", emoji: "🏆" },
    3: { name: "Europa League", emoji: "🏆" },
    40: { name: "Championship", emoji: "🏴󠁧󠁢󠁥󠁮󠁧󠁿" },
    141: { name: "Segunda División", emoji: "🇪🇸" },
    136: { name: "Serie B", emoji: "🇮🇹" },
    79: { name: "2. Bundesliga", emoji: "🇩🇪" },
    62: { name: "Ligue 2", emoji: "🇫🇷" },
  };

  function getLeagueDisplay(leagueId) {
    return leagueInfo[leagueId] || { name: "League", emoji: "⚽" };
  }

  onMount(async () => {
    saveSeason(season);
    try {
      // Fetch today's fixtures
      const res = await fetch(`${API_URL}/api/fixtures/today`);
      if (res.ok) {
        const data = await res.json();
        todaysMatches = data.response || [];
        matchOfTheDay = data.match_of_the_day;
      }
    } catch (e) {
      console.error("Error loading today's matches:", e);
      error = "Could not load today's matches";
    } finally {
      loading = false;
    }
  });

  function formatTime(dateStr) {
    return new Date(dateStr).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  }
</script>

<div class="space-y-8 md:space-y-12 page-enter pb-12">
  <!-- Hero Section -->
  <div class="relative isolate overflow-hidden">
    <!-- Background Effects -->
    <div class="absolute inset-0 -z-10">
      <div
        class="absolute top-0 right-0 -translate-y-12 translate-x-12 w-96 h-96 bg-primary/20 rounded-full blur-3xl opacity-50"
      ></div>
      <div
        class="absolute bottom-0 left-0 translate-y-12 -translate-x-12 w-96 h-96 bg-secondary/20 rounded-full blur-3xl opacity-50"
      ></div>
    </div>

    <div
      class="glass-card p-8 md:p-12 lg:p-16 text-center relative overflow-hidden group border-white/5"
    >
      <div
        class="absolute inset-0 bg-gradient-to-b from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700"
      ></div>

      <div
        class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-accent mb-6 backdrop-blur-md"
      >
        <span class="relative flex h-2 w-2">
          <span
            class="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent opacity-75"
          ></span>
          <span class="relative inline-flex rounded-full h-2 w-2 bg-accent"
          ></span>
        </span>
        Live Predictions Available
      </div>

      <h1
        class="font-display text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold mb-6 tracking-tight leading-none"
      >
        <span
          class="text-transparent bg-clip-text bg-gradient-to-r from-white via-white to-slate-400"
          >Fixture</span
        ><span
          class="text-transparent bg-clip-text bg-gradient-to-r from-primary to-accent"
          >Cast</span
        >
      </h1>

      <p
        class="font-light text-lg sm:text-xl md:text-2xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed"
      >
        Next-generation football forecasting powered by <span
          class="text-white font-medium">ensemble machine learning</span
        >.
      </p>

      <div
        class="flex flex-col sm:flex-row justify-center gap-4 w-full max-w-md mx-auto relative z-10"
      >
        <Link
          to="/today"
          class="group relative px-8 py-4 rounded-xl bg-gradient-to-r from-primary to-blue-600 text-white font-bold shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 transition-all hover:-translate-y-0.5 overflow-hidden"
        >
          <div
            class="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300"
          ></div>
          <span class="relative flex items-center justify-center gap-2">
            Today's Fixtures
            <svg
              class="w-5 h-5 transition-transform group-hover:translate-x-1"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              ><path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M13 7l5 5m0 0l-5 5m5-5H6"
              /></svg
            >
          </span>
        </Link>
        <Link
          to="/predictions"
          class="px-8 py-4 rounded-xl bg-white/5 text-white font-bold border border-white/10 hover:bg-white/10 hover:border-white/20 transition-all hover:-translate-y-0.5 backdrop-blur-sm"
        >
          View AI Models
        </Link>
      </div>
    </div>
  </div>

  <!-- Match of the Day Section -->
  {#if loading}
    <!-- Match of the Day Skeleton -->
    <div class="space-y-4">
      <div class="flex items-center justify-between px-2">
        <div class="h-8 w-48 bg-white/10 rounded-lg animate-pulse"></div>
        <div class="h-6 w-32 bg-white/10 rounded-full animate-pulse"></div>
      </div>

      <div class="glass-card p-8 md:p-10 animate-pulse">
        <div
          class="flex flex-col md:flex-row items-center justify-between gap-8"
        >
          <!-- Home Team Skeleton -->
          <div class="flex-1 space-y-4">
            <div
              class="w-24 h-24 md:w-32 md:h-32 bg-white/10 rounded-full mx-auto"
            ></div>
            <div class="h-8 w-48 bg-white/10 rounded mx-auto"></div>
          </div>

          <!-- VS Skeleton -->
          <div class="space-y-2">
            <div class="h-6 w-16 bg-white/10 rounded mx-auto"></div>
            <div class="h-12 w-24 bg-white/10 rounded mx-auto"></div>
          </div>

          <!-- Away Team Skeleton -->
          <div class="flex-1 space-y-4">
            <div
              class="w-24 h-24 md:w-32 md:h-32 bg-white/10 rounded-full mx-auto"
            ></div>
            <div class="h-8 w-48 bg-white/10 rounded mx-auto"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Today's Matches Skeleton -->
    <div class="space-y-4">
      <div class="h-8 w-56 bg-white/10 rounded-lg animate-pulse"></div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {#each Array(6) as _}
          <MatchCardSkeleton />
        {/each}
      </div>
    </div>
  {:else if matchOfTheDay}
    <div class="relative">
      <div class="flex items-center justify-between mb-6 px-2">
        <div class="flex items-center gap-3">
          <div class="p-2 bg-amber-500/10 rounded-lg text-amber-400">
            <svg
              class="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              ><path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
              /></svg
            >
          </div>
          <h2 class="text-2xl font-display font-bold text-white">
            Match of the Day
          </h2>
        </div>
        <div
          class="text-sm font-medium text-slate-400 bg-white/5 px-3 py-1 rounded-full border border-white/5"
        >
          {getLeagueDisplay(matchOfTheDay.league?.id).emoji}
          {matchOfTheDay.league?.name || "League"}
        </div>
      </div>

      <Link
        to={`/prediction/${matchOfTheDay.fixture.id}?league=${matchOfTheDay.league?.id || 39}&season=${season}`}
        class="block group relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900 to-slate-950 border border-white/10 hover:border-primary/50 transition-all duration-500 hover:shadow-2xl hover:shadow-primary/10"
      >
        <!-- Background Glow -->
        <div
          class="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full bg-gradient-to-b from-primary/5 to-transparent opacity-50"
        ></div>

        <div class="relative p-8 md:p-10">
          <div
            class="flex flex-col md:flex-row items-center justify-between gap-8"
          >
            <!-- Home Team -->
            <div class="flex-1 text-center md:text-right group/team">
              <div class="relative inline-block">
                <div
                  class="absolute inset-0 bg-primary/20 blur-2xl rounded-full opacity-0 group-hover/team:opacity-100 transition-opacity"
                ></div>
                <img
                  src={matchOfTheDay.teams.home.logo}
                  alt={matchOfTheDay.teams.home.name}
                  class="relative w-24 h-24 md:w-32 md:h-32 mx-auto md:ml-auto object-contain drop-shadow-2xl transition-transform group-hover/team:scale-110 duration-300"
                />
              </div>
              <div
                class="mt-4 font-display font-bold text-xl md:text-3xl text-white"
              >
                {matchOfTheDay.teams.home.name}
              </div>
            </div>

            <!-- VS & Time -->
            <div class="px-4 text-center shrink-0 relative z-10">
              <div
                class="text-sm font-bold text-primary tracking-widest uppercase mb-2"
              >
                VS
              </div>
              <div
                class="text-4xl md:text-5xl font-display font-bold text-white mb-2 tracking-tight"
              >
                {formatTime(matchOfTheDay.fixture.date)}
              </div>
              <div
                class="text-sm font-medium text-slate-400 bg-white/5 px-4 py-1.5 rounded-full inline-block"
              >
                {new Date(matchOfTheDay.fixture.date).toLocaleDateString([], {
                  weekday: "long",
                  month: "long",
                  day: "numeric",
                })}
              </div>
            </div>

            <!-- Away Team -->
            <div class="flex-1 text-center md:text-left group/team">
              <div class="relative inline-block">
                <div
                  class="absolute inset-0 bg-secondary/20 blur-2xl rounded-full opacity-0 group-hover/team:opacity-100 transition-opacity"
                ></div>
                <img
                  src={matchOfTheDay.teams.away.logo}
                  alt={matchOfTheDay.teams.away.name}
                  class="relative w-24 h-24 md:w-32 md:h-32 mx-auto md:mr-auto object-contain drop-shadow-2xl transition-transform group-hover/team:scale-110 duration-300"
                />
              </div>
              <div
                class="mt-4 font-display font-bold text-xl md:text-3xl text-white"
              >
                {matchOfTheDay.teams.away.name}
              </div>
            </div>
          </div>

          <div class="mt-10 text-center">
            <span
              class="inline-flex items-center gap-2 px-6 py-3 bg-primary/10 hover:bg-primary/20 border border-primary/20 rounded-full text-primary font-bold transition-all group-hover:scale-105"
            >
              <svg
                class="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                ><path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                /></svg
              >
              View AI Analysis
            </span>
          </div>
        </div>
      </Link>
    </div>
  {:else if !error}
    <div class="glass-card p-12 text-center content-enter">
      <div
        class="w-16 h-16 bg-white/5 rounded-2xl flex items-center justify-center mx-auto mb-4 text-slate-400"
      >
        <svg
          class="w-8 h-8"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          ><path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
          /></svg
        >
      </div>
      <h3 class="font-display font-bold text-xl mb-2">No Matches Today</h3>
      <p class="text-slate-400">Check back tomorrow for new predictions!</p>
    </div>
  {/if}

  <!-- Today's Other Matches -->
  {#if todaysMatches.length > 1}
    <div class="content-enter">
      <div class="flex items-center justify-between mb-6 px-2">
        <h2 class="text-2xl font-display font-bold">Today's Matches</h2>
        <Link
          to="/today"
          class="text-sm font-medium text-primary hover:text-primary/80 transition-colors"
        >
          View all {todaysMatches.length} matches &rarr;
        </Link>
      </div>

      <div
        class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 stagger-enter"
      >
        {#each todaysMatches.slice(1, 7) as fixture}
          <Link
            to={`/prediction/${fixture.fixture.id}?league=${fixture.league?.id || 39}&season=${season}`}
            class="group glass-card p-4 hover:border-primary/30 transition-all hover:-translate-y-1"
          >
            <div
              class="flex items-center justify-between mb-3 text-xs text-slate-400"
            >
              <span>{fixture.league?.name}</span>
              <span class="font-mono">{formatTime(fixture.fixture.date)}</span>
            </div>

            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <img
                    src={fixture.teams.home.logo}
                    alt=""
                    class="w-8 h-8 object-contain"
                  />
                  <span
                    class="font-medium group-hover:text-white transition-colors"
                    >{fixture.teams.home.name}</span
                  >
                </div>
              </div>
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <img
                    src={fixture.teams.away.logo}
                    alt=""
                    class="w-8 h-8 object-contain"
                  />
                  <span
                    class="font-medium group-hover:text-white transition-colors"
                    >{fixture.teams.away.name}</span
                  >
                </div>
              </div>
            </div>
          </Link>
        {/each}
      </div>
    </div>
  {/if}

  <!-- Quick Access Grid -->
  <div class="grid grid-cols-1 md:grid-cols-3 gap-6 stagger-enter">
    <Link to="/fixtures" class="glass-card p-6 group relative overflow-hidden">
      <div
        class="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity transform group-hover:scale-110 duration-500"
      >
        <svg
          class="w-24 h-24"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          ><path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.5"
            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
          /></svg
        >
      </div>
      <div
        class="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center text-blue-400 mb-4 group-hover:bg-blue-500/20 transition-colors"
      >
        <svg
          class="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          ><path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
          /></svg
        >
      </div>
      <h3
        class="text-xl font-display font-bold mb-2 group-hover:text-primary transition-colors"
      >
        Fixtures
      </h3>
      <p class="text-sm text-slate-400 leading-relaxed">
        Browse matches playing today across 14 major leagues.
      </p>
    </Link>

    <Link to="/teams" class="glass-card p-6 group relative overflow-hidden">
      <div
        class="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity transform group-hover:scale-110 duration-500"
      >
        <svg
          class="w-24 h-24"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          ><path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.5"
            d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
          /></svg
        >
      </div>
      <div
        class="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400 mb-4 group-hover:bg-emerald-500/20 transition-colors"
      >
        <svg
          class="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          ><path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
          /></svg
        >
      </div>
      <h3
        class="text-xl font-display font-bold mb-2 group-hover:text-emerald-400 transition-colors"
      >
        Team Stats
      </h3>
      <p class="text-sm text-slate-400 leading-relaxed">
        Analyze detailed team statistics and form guides.
      </p>
    </Link>

    <Link
      to="/predictions"
      class="glass-card p-6 group relative overflow-hidden"
    >
      <div
        class="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity transform group-hover:scale-110 duration-500"
      >
        <svg
          class="w-24 h-24"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          ><path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.5"
            d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
          /></svg
        >
      </div>
      <div
        class="w-12 h-12 rounded-xl bg-purple-500/10 flex items-center justify-center text-purple-400 mb-4 group-hover:bg-purple-500/20 transition-colors"
      >
        <svg
          class="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          ><path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
          /></svg
        >
      </div>
      <h3
        class="text-xl font-display font-bold mb-2 group-hover:text-purple-400 transition-colors"
      >
        AI Models
      </h3>
      <p class="text-sm text-slate-400 leading-relaxed">
        Access predictions from our ensemble of 11 ML models.
      </p>
    </Link>
  </div>
</div>

<style>
  /* Page-specific animations handled by global CSS */
</style>
