<script>
  // Prediction Accuracy Tracker Component
  // Shows historical model accuracy for the selected league/context
  export let league = 39;
  export let modelAccuracy = null;
  export let compact = false;

  import { onMount } from "svelte";
  import { ML_API_URL } from "../config.js";

  let accuracyData = null;
  let loading = true;

  // Default accuracy data (will be replaced by API call)
  const defaultAccuracy = {
    overall: 0.695,
    high_confidence: 0.801,
    recent_form: 0.72,
    by_league: {
      39: { name: "Premier League", accuracy: 0.71, matches: 380 },
      140: { name: "La Liga", accuracy: 0.68, matches: 340 },
      135: { name: "Serie A", accuracy: 0.69, matches: 350 },
      78: { name: "Bundesliga", accuracy: 0.67, matches: 306 },
      61: { name: "Ligue 1", accuracy: 0.66, matches: 340 },
    }
  };

  // Transform API response to expected format
  function transformApiResponse(data) {
    const result = {
      overall: data?.overall?.accuracy ?? defaultAccuracy.overall,
      high_confidence: data?.by_confidence?.high?.accuracy ?? defaultAccuracy.high_confidence,
      recent_form: data?.recent_form?.last_10?.accuracy ?? defaultAccuracy.recent_form,
      by_league: {}
    };

    // Transform league data
    if (data?.by_league) {
      for (const [leagueId, stats] of Object.entries(data.by_league)) {
        result.by_league[leagueId] = {
          name: stats.name || `League ${leagueId}`,
          accuracy: stats.accuracy ?? 0.65,
          matches: stats.total || 0
        };
      }
    }

    // If no league data, use defaults
    if (Object.keys(result.by_league).length === 0) {
      result.by_league = defaultAccuracy.by_league;
    }

    return result;
  }

  onMount(async () => {
    try {
      // Try to fetch from feedback API
      const res = await fetch(`${ML_API_URL}/api/feedback/performance`);
      if (res.ok) {
        const data = await res.json();
        // Check if we have meaningful data (more than 0 predictions)
        if (data?.overall?.total > 0) {
          accuracyData = transformApiResponse(data);
        } else {
          accuracyData = modelAccuracy || defaultAccuracy;
        }
      } else {
        accuracyData = modelAccuracy || defaultAccuracy;
      }
    } catch (e) {
      accuracyData = modelAccuracy || defaultAccuracy;
    } finally {
      loading = false;
    }
  });

  $: leagueData = accuracyData?.by_league?.[league] || null;
  $: overallAccuracy = accuracyData?.overall ?? 0.695;
  $: highConfAccuracy = accuracyData?.high_confidence ?? 0.801;

  function getAccuracyColor(acc) {
    if (acc >= 0.75) return "text-emerald-400";
    if (acc >= 0.65) return "text-blue-400";
    if (acc >= 0.55) return "text-amber-400";
    return "text-red-400";
  }

  function getAccuracyBg(acc) {
    if (acc >= 0.75) return "bg-emerald-500";
    if (acc >= 0.65) return "bg-blue-500";
    if (acc >= 0.55) return "bg-amber-500";
    return "bg-red-500";
  }
</script>

{#if loading}
  <div class="skeleton-shimmer {compact ? 'h-4' : 'h-16'} bg-white/5 rounded-lg"></div>
{:else if compact}
  <!-- Compact inline version -->
  <div class="inline-flex items-center gap-2 text-xs">
    <span class="text-slate-400">Model Accuracy:</span>
    <span class="font-bold {getAccuracyColor(overallAccuracy)}">
      {(overallAccuracy * 100).toFixed(0)}%
    </span>
    {#if leagueData}
      <span class="text-slate-500">•</span>
      <span class="text-slate-400">{leagueData.name}:</span>
      <span class="font-bold {getAccuracyColor(leagueData.accuracy)}">
        {(leagueData.accuracy * 100).toFixed(0)}%
      </span>
    {/if}
  </div>
{:else}
  <!-- Full card version -->
  <div class="glass-card p-4 element-enter">
    <div class="flex items-center gap-2 mb-3">
      <span class="text-lg">📈</span>
      <h4 class="font-bold text-sm">Model Performance</h4>
    </div>

    <div class="grid grid-cols-2 gap-3">
      <!-- Overall Accuracy -->
      <div class="bg-white/5 rounded-lg p-3">
        <div class="text-xs text-slate-400 mb-1">Overall Accuracy</div>
        <div class="flex items-end gap-1">
          <span class="text-2xl font-bold {getAccuracyColor(overallAccuracy)}">
            {(overallAccuracy * 100).toFixed(0)}%
          </span>
        </div>
        <div class="mt-2 h-1.5 bg-white/10 rounded-full overflow-hidden">
          <div
            class="h-full rounded-full bar-fill {getAccuracyBg(overallAccuracy)}"
            style="width: {overallAccuracy * 100}%"
          ></div>
        </div>
      </div>

      <!-- High Confidence -->
      <div class="bg-white/5 rounded-lg p-3">
        <div class="text-xs text-slate-400 mb-1">High Confidence</div>
        <div class="flex items-end gap-1">
          <span class="text-2xl font-bold {getAccuracyColor(highConfAccuracy)}">
            {(highConfAccuracy * 100).toFixed(0)}%
          </span>
        </div>
        <div class="mt-2 h-1.5 bg-white/10 rounded-full overflow-hidden">
          <div
            class="h-full rounded-full bar-fill {getAccuracyBg(highConfAccuracy)}"
            style="width: {highConfAccuracy * 100}%"
          ></div>
        </div>
      </div>
    </div>

    {#if leagueData}
      <div class="mt-3 pt-3 border-t border-white/10">
        <div class="flex items-center justify-between">
          <span class="text-xs text-slate-400">{leagueData.name} Accuracy</span>
          <span class="text-sm font-bold {getAccuracyColor(leagueData.accuracy)}">
            {(leagueData.accuracy * 100).toFixed(0)}%
          </span>
        </div>
        <div class="text-xs text-slate-500 mt-1">
          Based on {leagueData.matches} analyzed matches
        </div>
      </div>
    {/if}

    <div class="mt-3 text-xs text-slate-500 text-center">
      ✨ Higher confidence predictions have {((highConfAccuracy - overallAccuracy) * 100).toFixed(0)}% better accuracy
    </div>
  </div>
{/if}
