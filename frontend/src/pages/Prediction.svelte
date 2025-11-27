<script>
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import HeadToHead from "../components/HeadToHead.svelte";
  import SkeletonLoader from "../components/SkeletonLoader.svelte";
  import ConfidenceBadge from "../components/ConfidenceBadge.svelte";
  import AccuracyTracker from "../components/AccuracyTracker.svelte";
  import { favorites, toggleFixtureFavorite, isFixtureFavorite } from "../services/favoritesStore.js";
  import { addToHistory } from "../services/historyStore.js";
  import { exportPredictionsToCSV, exportPredictionsToPDF } from "../services/exportService.js";
  import { compareStore } from "../services/compareStore.js";
  import { ML_API_URL } from "../config.js";
  import { getCurrentSeason } from "../services/season.js";

  export let id; // Fixture ID from router

  let data = null;
  let loading = true;
  let error = null;
  let league = 39;
  let season = getCurrentSeason();
  let predictionRequestToken = 0;
  let showDetails = true;
  let isMobile = false;

  // Use reactive auto-subscription ($ prefix) - automatically unsubscribes
  $: currentFavorites = $favorites;
  $: compareFixtures = $compareStore?.fixtures || [];

  function toggleCompare() {
    compareStore.addFixture(parseInt(id), league);
  }

  function isInCompare() {
    return compareFixtures.includes(parseInt(id));
  }

  // Get max confidence for badge
  $: maxConfidence = data?.prediction ? Math.max(
    data.prediction.home_win_prob || 0,
    data.prediction.draw_prob || 0,
    data.prediction.away_win_prob || 0
  ) : 0;

  onMount(async () => {
    if (typeof window !== "undefined") {
      isMobile = window.innerWidth < 768;
      showDetails = !isMobile;
      const params = new URLSearchParams(window.location.search);
      const leagueParam = parseInt(params.get("league") || "", 10);
      const seasonParam = parseInt(params.get("season") || "", 10);
      if (!Number.isNaN(leagueParam)) league = leagueParam;
      if (!Number.isNaN(seasonParam)) season = seasonParam;
    }
    await loadPrediction();
  });

  async function loadPrediction() {
    const requestId = ++predictionRequestToken;
    try {
      const res = await fetch(
        `${ML_API_URL}/api/prediction/${id}?league=${league}&season=${season}`,
      );
      if (!res.ok) throw new Error("Failed to load prediction");
      const payload = await res.json();
      if (requestId !== predictionRequestToken) return;
      data = payload;
      if (payload?.fixture_details?.league?.id) {
        league = payload.fixture_details.league.id;
      }
      if (payload?.fixture_details?.fixture?.season) {
        season = payload.fixture_details.fixture.season;
      }

      // Add to history
      if (data && data.fixture_details) {
        addToHistory({
          fixture_id: id,
          home_team: data.fixture_details.teams?.home?.name || "Unknown",
          away_team: data.fixture_details.teams?.away?.name || "Unknown",
          home_win_prob: data.prediction?.home_win_prob,
          draw_prob: data.prediction?.draw_prob,
          away_win_prob: data.prediction?.away_win_prob,
          predicted_score: data.prediction?.predicted_scoreline,
          league_id: data.fixture_details?.league?.id || league,
          season,
          confidence: Math.max(
            data.prediction?.home_win_prob || 0,
            data.prediction?.draw_prob || 0,
            data.prediction?.away_win_prob || 0
          ),
        });
      }
    } catch (e) {
      error = e.message;
    } finally {
      if (requestId === predictionRequestToken) {
        loading = false;
      }
    }
  }

  function formatAnalysis(text) {
    if (!text) return "";
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-bold">$1</strong>') // Bold
      .replace(/\*(.*?)\*/g, '<em class="text-slate-300 italic">$1</em>') // Italic
      .replace(/\n\n/g, "</p><p class='mb-4'>") // Paragraphs
      .replace(/\n/g, "<br/>") // Line breaks
      .replace(/^• (.*?)(<br\/>|$)/gm, '<li class="ml-6 mb-2 list-disc text-slate-300">$1</li>') // Bullet points
      .replace(/<\/li><br\/>/g, '</li>'); // Clean up list breaks
  }

  function getConfidenceColor(prob) {
    if (prob > 0.7) return "text-emerald-400";
    if (prob > 0.5) return "text-blue-400";
    return "text-amber-400";
  }

  function toggleFavorite() {
    if (data && data.fixture_details) {
      toggleFixtureFavorite({
        id: parseInt(id),
        home: data.fixture_details.teams.home.name,
        away: data.fixture_details.teams.away.name,
        date: data.fixture_details.fixture.date,
      });
    }
  }

  function exportCSV() {
    if (data && data.prediction && data.fixture_details) {
      exportPredictionsToCSV([
        {
          date: data.fixture_details.fixture.date,
          home_team: data.fixture_details.teams.home.name,
          away_team: data.fixture_details.teams.away.name,
          ...data.prediction,
        },
      ]);
    }
  }

  function exportPDF() {
    if (data && data.prediction && data.fixture_details) {
      exportPredictionsToPDF([
        {
          date: data.fixture_details.fixture.date,
          home_team: data.fixture_details.teams.home.name,
          away_team: data.fixture_details.teams.away.name,
          ...data.prediction,
        },
      ]);
    }
  }

  function toggleDetails() {
    showDetails = !showDetails;
  }
</script>

{#if loading}
  <!-- Skeleton Loading State -->
  <div class="max-w-5xl mx-auto space-y-6 md:space-y-8 px-1">
    <div class="flex gap-2 justify-center">
      <SkeletonLoader type="bar" width="100px" height="36px" />
      <SkeletonLoader type="bar" width="80px" height="36px" />
      <SkeletonLoader type="bar" width="80px" height="36px" />
    </div>
    <SkeletonLoader type="prediction" />
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="lg:col-span-2">
        <SkeletonLoader type="card" />
      </div>
      <SkeletonLoader type="stats" />
    </div>
  </div>
{:else if error}
  <div class="text-center text-danger py-10">Error: {error}</div>
{:else if data}
  <div class="max-w-5xl mx-auto space-y-6 md:space-y-8 page-enter px-1">
    <!-- Confidence Badge (prominent) -->
    <div class="flex justify-center element-enter">
      <ConfidenceBadge confidence={maxConfidence} size="lg" />
    </div>

    <!-- Action Buttons - Scrollable on mobile -->
    <div class="flex gap-2 md:gap-3 justify-start md:justify-center overflow-x-auto pb-2 hide-scrollbar -mx-1 px-1 element-enter stagger-1">
      <button
        on:click={toggleFavorite}
        class="flex-shrink-0 px-3 md:px-4 py-2 rounded-lg text-sm touch-target btn-interact {isFixtureFavorite(parseInt(id), currentFavorites)
          ? 'bg-accent text-white'
          : 'bg-white/10 hover:bg-white/20 active:bg-white/30'}"
      >
        {isFixtureFavorite(parseInt(id), currentFavorites) ? '⭐ Favorited' : '☆ Favorite'}
      </button>
      <button
        on:click={toggleCompare}
        class="flex-shrink-0 px-3 md:px-4 py-2 rounded-lg text-sm touch-target btn-interact {isInCompare()
          ? 'bg-purple-500 text-white'
          : 'bg-white/10 hover:bg-white/20 active:bg-white/30'}"
      >
        {isInCompare() ? '⚖️ In Compare' : '⚖️ Compare'}
      </button>
      <button
        on:click={exportCSV}
        class="flex-shrink-0 px-3 md:px-4 py-2 bg-white/10 rounded-lg hover:bg-white/20 active:bg-white/30 text-sm touch-target btn-interact"
      >
        📊 CSV
      </button>
      <button
        on:click={exportPDF}
        class="flex-shrink-0 px-3 md:px-4 py-2 bg-white/10 rounded-lg hover:bg-white/20 active:bg-white/30 text-sm touch-target btn-interact"
      >
        📄 PDF
      </button>
    </div>

    <!-- Match Header -->
    <div class="glass-card p-4 md:p-8 text-center relative overflow-hidden group element-enter stagger-2">
      <div
        class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-accent to-transparent"
      ></div>
      <div
        class="absolute inset-0 bg-accent/5 opacity-0 group-hover:opacity-10 transition-opacity duration-500"
      ></div>

      <!-- Competition Badge -->
      {#if data.fixture_details.league}
        {@const league = data.fixture_details.league}
        {@const isEuropean = [2, 3, 848].includes(league.id)}
        {@const isCup = [45, 48].includes(league.id)}
        {@const round = league.round || ''}
        <div class="flex justify-center mb-4">
          <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium
            {isEuropean ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30' :
             isCup ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' :
             'bg-accent/20 text-accent border border-accent/30'}">
            {#if league.logo}
              <img src={league.logo} alt="" class="w-4 h-4" />
            {/if}
            <span>{league.name}</span>
            {#if round}
              <span class="text-slate-400">•</span>
              <span class="text-slate-300">{round}</span>
            {/if}
          </div>
        </div>
      {/if}

      <div
        class="flex flex-col md:flex-row justify-between items-center mb-6 md:mb-8 gap-4 md:gap-6"
      >
        <!-- Home Team -->
        <Link
          to={`/team/${data.fixture_details.teams.home.id}?league=${data.fixture_details.league?.id || 39}`}
          class="flex flex-col items-center w-full md:w-1/3 group cursor-pointer"
        >
          <div class="relative">
            <div
              class="absolute inset-0 bg-accent/20 blur-xl rounded-full opacity-20 group-hover:opacity-40 transition-opacity"
            ></div>
            <img
              src={data.fixture_details.teams.home.logo}
              alt=""
              class="w-16 h-16 sm:w-20 sm:h-20 md:w-24 md:h-24 lg:w-32 lg:h-32 object-contain mb-2 md:mb-4 drop-shadow-2xl relative z-10 transform group-hover:scale-110 transition-transform duration-300"
            />
          </div>
          <h2 class="text-lg sm:text-xl md:text-2xl font-bold text-white group-hover:text-accent transition-colors text-center">
            {data.fixture_details.teams.home.name}
          </h2>
          <div class="text-xs md:text-sm text-slate-400 mt-1">Home</div>
        </Link>

        <!-- Score & Time -->
        <div class="flex flex-col items-center w-full md:w-1/3 z-10 order-first md:order-none py-2">
          <div
            class="text-[10px] md:text-xs font-bold text-accent uppercase tracking-[0.15em] md:tracking-[0.2em] mb-2 md:mb-3"
          >
            Predicted Score
          </div>
          <div
            class="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-mono font-bold text-white tracking-tighter mb-2 md:mb-3 drop-shadow-lg"
          >
            {data.prediction.predicted_scoreline}
          </div>
          <div
            class="px-3 md:px-4 py-1 rounded-full bg-white/5 border border-white/10 text-[10px] md:text-xs text-slate-300 backdrop-blur-sm"
          >
            {new Date(data.fixture_details.fixture.date).toLocaleString(
              undefined,
              {
                weekday: "short",
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              },
            )}
          </div>
        </div>

        <!-- Away Team -->
        <Link
          to={`/team/${data.fixture_details.teams.away.id}?league=${data.fixture_details.league?.id || 39}`}
          class="flex flex-col items-center w-full md:w-1/3 group cursor-pointer"
        >
          <div class="relative">
            <div
              class="absolute inset-0 bg-rose-500/20 blur-xl rounded-full opacity-20 group-hover:opacity-40 transition-opacity"
            ></div>
            <img
              src={data.fixture_details.teams.away.logo}
              alt=""
              class="w-16 h-16 sm:w-20 sm:h-20 md:w-24 md:h-24 lg:w-32 lg:h-32 object-contain mb-2 md:mb-4 drop-shadow-2xl relative z-10 transform group-hover:scale-110 transition-transform duration-300"
            />
          </div>
          <h2 class="text-lg sm:text-xl md:text-2xl font-bold text-white group-hover:text-accent transition-colors text-center">
            {data.fixture_details.teams.away.name}
          </h2>
          <div class="text-xs md:text-sm text-slate-400 mt-1">Away</div>
        </Link>
      </div>

      <!-- Probability Bars -->
      <div class="max-w-2xl mx-auto">
        <div
          class="flex justify-between text-xs md:text-sm font-bold text-slate-300 px-1 mb-2"
        >
          <span class="text-emerald-400">Home</span>
          <span class="text-slate-400">Draw</span>
          <span class="text-rose-400">Away</span>
        </div>
        <div
          class="flex h-5 md:h-6 rounded-full overflow-hidden bg-secondary/50 mb-2 shadow-inner ring-1 ring-white/10"
        >
          <div
            class="bg-gradient-to-r from-emerald-600 to-emerald-400 flex items-center justify-center text-[9px] md:text-[10px] font-bold text-black/70"
            style="width: {data.prediction.home_win_prob * 100}%"
          >
            {(data.prediction.home_win_prob * 100).toFixed(0)}%
          </div>
          <div
            class="bg-slate-500 flex items-center justify-center text-[9px] md:text-[10px] font-bold text-white/70"
            style="width: {data.prediction.draw_prob * 100}%"
          >
            {(data.prediction.draw_prob * 100).toFixed(0)}%
          </div>
          <div
            class="bg-gradient-to-r from-rose-400 to-rose-600 flex items-center justify-center text-[9px] md:text-[10px] font-bold text-black/70"
            style="width: {data.prediction.away_win_prob * 100}%"
          >
            {(data.prediction.away_win_prob * 100).toFixed(0)}%
          </div>
        </div>
      </div>
    </div>

    <div class="flex justify-center mt-2 md:hidden">
      <button
        class="px-4 py-2 bg-white/10 rounded-lg border border-white/10 text-sm btn-interact"
        on:click={toggleDetails}
      >
        {showDetails ? "Hide full analysis" : "Show full analysis & stats"}
      </button>
    </div>

    <!-- Analysis & Stats Grid -->
    <div class={`grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6 element-enter stagger-3 ${!showDetails && isMobile ? 'hidden' : ''}`}>
      <!-- AI Analysis -->
      <div class="lg:col-span-2 glass-card p-4 md:p-8 relative overflow-hidden">
        <div class="absolute top-0 right-0 p-4 opacity-10 hidden md:block">
          <svg
            class="w-24 md:w-32 h-24 md:h-32 text-accent"
            fill="currentColor"
            viewBox="0 0 24 24"
            ><path
              d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17h-2v-2h2v2zm2.07-7.75l-.9.92C13.45 12.9 13 13.5 13 15h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H8c0-2.21 1.79-4 4-4s4 1.79 4 4c0 .88-.36 1.68-.93 2.25z"
            /></svg
          >
        </div>
        <h3 class="text-lg md:text-xl font-bold mb-4 md:mb-6 flex items-center gap-2 md:gap-3">
          <span
            class="flex items-center justify-center w-7 h-7 md:w-8 md:h-8 rounded-lg bg-accent/20 text-accent text-sm md:text-base"
            >✨</span
          >
          AI Match Analysis
        </h3>
        <div
          class="prose prose-invert prose-sm md:prose-lg max-w-none text-slate-300 leading-relaxed space-y-3 md:space-y-4"
        >
          <p class="mb-4">{@html formatAnalysis(data.analysis)}</p>
        </div>
      </div>

      <!-- Key Stats & Insights -->
      <div class="space-y-4 md:space-y-6">
        <!-- Advanced Metrics -->
        <div class="glass-card p-4 md:p-6">
          <h3 class="text-base md:text-lg font-bold mb-4 md:mb-6 flex items-center gap-2">
            <span class="text-accent">📊</span> Advanced Metrics
          </h3>

          <div class="space-y-4 md:space-y-6">
            <!-- BTTS -->
            <div>
              <div class="flex justify-between items-center mb-2">
                <span class="text-slate-400 text-xs md:text-sm">Both Teams to Score</span>
                <span class="font-mono font-bold text-white text-sm md:text-base"
                  >{(data.prediction.btts_prob * 100).toFixed(0)}%</span
                >
              </div>
              <div class="h-2 bg-white/5 rounded-full overflow-hidden">
                <div
                  class="h-full bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full"
                  style="width: {data.prediction.btts_prob * 100}%"
                ></div>
              </div>
            </div>

            <!-- Over 2.5 -->
            <div>
              <div class="flex justify-between items-center mb-2">
                <span class="text-slate-400 text-xs md:text-sm">Over 2.5 Goals</span>
                <span class="font-mono font-bold text-white text-sm md:text-base"
                  >{(data.prediction.over25_prob * 100).toFixed(0)}%</span
                >
              </div>
              <div class="h-2 bg-white/5 rounded-full overflow-hidden">
                <div
                  class="h-full bg-gradient-to-r from-orange-500 to-amber-400 rounded-full"
                  style="width: {data.prediction.over25_prob * 100}%"
                ></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Model Confidence -->
        <div class="glass-card p-4 md:p-6">
          <h3 class="text-base md:text-lg font-bold mb-3 md:mb-4 flex items-center gap-2">
            <span class="text-accent">🎯</span> System Confidence
          </h3>

          <div class="flex items-center justify-center py-2 md:py-4">
            <div class="relative w-24 h-24 md:w-32 md:h-32 flex items-center justify-center">
              <svg class="w-full h-full transform -rotate-90">
                <circle
                  cx="50%"
                  cy="50%"
                  r="45%"
                  stroke="currentColor"
                  stroke-width="8"
                  fill="transparent"
                  class="text-white/5"
                />
                <circle
                  cx="50%"
                  cy="50%"
                  r="45%"
                  stroke="currentColor"
                  stroke-width="8"
                  fill="transparent"
                  class={getConfidenceColor(
                    Math.max(
                      data.prediction.home_win_prob,
                      data.prediction.away_win_prob,
                    ),
                  )}
                  stroke-dasharray="283"
                  stroke-dashoffset={283 -
                    283 *
                      Math.max(
                        data.prediction.home_win_prob,
                        data.prediction.away_win_prob,
                      )}
                  stroke-linecap="round"
                />
              </svg>
              <div class="absolute text-center">
                <div class="text-xl md:text-2xl font-bold text-white">
                  {(
                    Math.max(
                      data.prediction.home_win_prob,
                      data.prediction.away_win_prob,
                    ) * 100
                  ).toFixed(0)}%
                </div>
                <div
                  class="text-[8px] md:text-[10px] uppercase tracking-wider text-slate-400"
                >
                  Certainty
                </div>
              </div>
            </div>
          </div>

          <div class="text-center text-[10px] md:text-xs text-slate-500 mt-1 md:mt-2">
            Based on consensus of 8 statistical models
          </div>
        </div>

        <!-- Model Accuracy Tracker -->
        <AccuracyTracker league={data.fixture_details?.league?.id || 39} />
      </div>
    </div>

    <!-- Head-to-Head Section -->
    <div class={!showDetails && isMobile ? 'hidden' : ''}>
      {#if data.fixture_details}
        <HeadToHead
          homeTeam={data.fixture_details.teams.home}
          awayTeam={data.fixture_details.teams.away}
        />
      {/if}
    </div>
  </div>
{/if}
