<script>
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";

  let metrics = null;
  let loading = true;
  let error = null;
  const BACKEND_API = import.meta.env.VITE_BACKEND_API || "http://localhost:8000";

  onMount(async () => {
    try {
      const res = await fetch(`${BACKEND_API}/api/metrics/summary`);
      if (!res.ok) throw new Error("Failed to load metrics");
      metrics = await res.json();
    } catch (e) {
      error = e.message;
      console.error("Error loading metrics:", e);
    } finally {
      loading = false;
    }
  });

  function getAccuracyColor(accuracy) {
    if (accuracy >= 0.65) return "text-emerald-400";
    if (accuracy >= 0.55) return "text-blue-400";
    return "text-amber-400";
  }

  function getCalibrationColor(error) {
    if (error < 0.1) return "text-emerald-400";
    if (error < 0.2) return "text-blue-400";
    return "text-amber-400";
  }
</script>

<div class="space-y-6 page-enter">
  <!-- Header -->
  <div class="glass-card p-6 md:p-8">
    <div class="flex justify-between items-center mb-4">
      <div>
        <h1 class="text-3xl md:text-4xl font-bold mb-2">Model Performance Dashboard</h1>
        <p class="text-slate-400">Track prediction accuracy and model calibration over time</p>
      </div>
      <Link to="/" class="px-4 py-2 bg-accent text-white rounded-lg font-medium hover:bg-accent/90 transition">
        ← Back
      </Link>
    </div>
  </div>

  {#if loading}
    <div class="glass-card p-8 text-center">
      <div class="animate-spin inline-block">⚙️</div>
      <p class="mt-3 text-slate-400">Loading metrics...</p>
    </div>
  {:else if error}
    <div class="glass-card p-6 border border-red-500/30 bg-red-500/5">
      <p class="text-red-400">Error: {error}</p>
      <p class="text-sm text-slate-400 mt-2">Check that the backend API is running</p>
    </div>
  {:else if metrics}
    <!-- 7-Day Summary -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="glass-card p-4">
        <div class="text-slate-400 text-sm font-medium mb-2">7-Day Accuracy</div>
        <div class={`text-3xl font-bold ${getAccuracyColor(metrics["7_day"].accuracy)}`}>
          {(metrics["7_day"].accuracy * 100).toFixed(1)}%
        </div>
        <div class="text-xs text-slate-500 mt-2">
          {metrics["7_day"].correct_predictions} / {metrics["7_day"].total_predictions} correct
        </div>
      </div>

      <div class="glass-card p-4">
        <div class="text-slate-400 text-sm font-medium mb-2">Avg Confidence</div>
        <div class="text-3xl font-bold text-blue-400">
          {(metrics["7_day"].avg_confidence * 100).toFixed(0)}%
        </div>
        <div class="text-xs text-slate-500 mt-2">
          Range: {(metrics["7_day"].min_confidence * 100).toFixed(0)}%–{(metrics["7_day"].max_confidence * 100).toFixed(0)}%
        </div>
      </div>

      <div class="glass-card p-4">
        <div class="text-slate-400 text-sm font-medium mb-2">Calibration Error</div>
        <div class={`text-3xl font-bold ${getCalibrationColor(metrics["7_day"].avg_calibration_error)}`}>
          {(metrics["7_day"].avg_calibration_error * 100).toFixed(1)}%
        </div>
        <div class="text-xs text-slate-500 mt-2">
          Max: {(metrics["7_day"].max_calibration_error * 100).toFixed(1)}%
        </div>
      </div>

      <div class="glass-card p-4">
        <div class="text-slate-400 text-sm font-medium mb-2">30-Day Accuracy</div>
        <div class={`text-3xl font-bold ${getAccuracyColor(metrics["30_day"].accuracy)}`}>
          {(metrics["30_day"].accuracy * 100).toFixed(1)}%
        </div>
        <div class="text-xs text-slate-500 mt-2">
          {metrics["30_day"].correct_predictions} / {metrics["30_day"].total_predictions} correct
        </div>
      </div>
    </div>

    <!-- Model Comparison -->
    {#if Object.keys(metrics.model_comparison).length > 0}
      <div class="glass-card p-6">
        <h2 class="text-xl font-bold mb-4 flex items-center gap-2">
          <span>📊</span> Individual Model Performance
        </h2>

        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-white/10">
                <th class="text-left py-3 px-4 font-medium text-slate-400">Model</th>
                <th class="text-center py-3 px-4 font-medium text-slate-400">Predictions</th>
                <th class="text-center py-3 px-4 font-medium text-slate-400">Correct</th>
                <th class="text-right py-3 px-4 font-medium text-slate-400">Accuracy</th>
              </tr>
            </thead>
            <tbody>
              {#each Object.entries(metrics.model_comparison) as [model, stats]}
                <tr class="border-t border-white/5 hover:bg-white/5 transition">
                  <td class="py-3 px-4 font-medium">{model}</td>
                  <td class="py-3 px-4 text-center text-slate-300">{stats.total}</td>
                  <td class="py-3 px-4 text-center text-slate-300">{stats.correct}</td>
                  <td class="py-3 px-4 text-right">
                    <span class={`font-bold ${getAccuracyColor(stats.accuracy)}`}>
                      {(stats.accuracy * 100).toFixed(1)}%
                    </span>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    {/if}

    <!-- All-Time Summary -->
    <div class="glass-card p-6">
      <h2 class="text-xl font-bold mb-4">All-Time Performance</h2>
      <div class="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div>
          <div class="text-slate-400 text-sm">Total Predictions</div>
          <div class="text-2xl font-bold mt-1">{metrics.all_time.total_predictions}</div>
        </div>
        <div>
          <div class="text-slate-400 text-sm">Correct</div>
          <div class="text-2xl font-bold text-emerald-400 mt-1">{metrics.all_time.correct_predictions}</div>
        </div>
        <div>
          <div class="text-slate-400 text-sm">Overall Accuracy</div>
          <div class={`text-2xl font-bold mt-1 ${getAccuracyColor(metrics.all_time.accuracy)}`}>
            {(metrics.all_time.accuracy * 100).toFixed(1)}%
          </div>
        </div>
      </div>
    </div>

    <!-- Last Updated -->
    <div class="text-center text-xs text-slate-500">
      Last updated: {new Date(metrics.last_updated).toLocaleString()}
    </div>
  {/if}
</div>

<style>
  :global(.page-enter) {
    animation: fadeIn 0.3s ease-out;
  }

  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(10px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
</style>
