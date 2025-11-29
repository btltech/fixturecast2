<script>
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";

  let metrics = null;
  let backtestHistory = null;
  let backtestSummary = null;
  let livePredictions = null;
  let loading = true;
  let error = null;
  const BACKEND_API = import.meta.env.VITE_BACKEND_API || "http://localhost:8000";
  const ML_API = import.meta.env.VITE_ML_API || "http://localhost:8001";

  // Password protection
  const ADMIN_PASSWORD = import.meta.env.VITE_ADMIN_PASSWORD || "fixturecast2025";
  let isAuthenticated = false;
  let passwordInput = "";
  let authError = "";

  // Tab state
  let activeTab = "summary"; // 'summary', 'history', or 'live'

  // Auto-refresh for live tab
  let refreshInterval = null;

  function handleLogin() {
    if (passwordInput === ADMIN_PASSWORD) {
      isAuthenticated = true;
      authError = "";
      // Store in session so refresh doesn't log out
      sessionStorage.setItem("admin_auth", "true");
      loadMetrics();
    } else {
      authError = "Incorrect password";
      passwordInput = "";
    }
  }

  function handleKeydown(event) {
    if (event.key === "Enter") {
      handleLogin();
    }
  }

  // Sorting state
  let sortColumn = "accuracy";
  let sortDirection = "desc"; // 'asc' or 'desc'

  async function loadMetrics() {
    try {
      // Load metrics, backtest history, and live predictions in parallel
      const [metricsRes, backtestRes, liveRes] = await Promise.all([
        fetch(`${BACKEND_API}/api/metrics/summary`).catch(() => null),
        fetch(`${BACKEND_API}/api/metrics/backtest-history?limit=52`).catch(() => null),
        fetch(`${ML_API}/api/metrics/history?limit=50`).catch(() => null)
      ]);

      if (metricsRes?.ok) {
        metrics = await metricsRes.json();
      }

      if (backtestRes?.ok) {
        const backtestData = await backtestRes.json();
        backtestHistory = backtestData.history || [];
        backtestSummary = backtestData.summary || null;
      }

      if (liveRes?.ok) {
        const liveData = await liveRes.json();
        livePredictions = liveData.predictions || [];
      }

      if (!metrics && !backtestHistory && !livePredictions) {
        throw new Error("Failed to load any metrics data");
      }
    } catch (e) {
      error = e.message;
      console.error("Error loading metrics:", e);
    } finally {
      loading = false;
    }
  }

  async function refreshLivePredictions() {
    try {
      const res = await fetch(`${ML_API}/api/metrics/history?limit=50`);
      if (res.ok) {
        const data = await res.json();
        livePredictions = data.predictions || [];
      }
    } catch (e) {
      console.error("Error refreshing live predictions:", e);
    }
  }

  onMount(() => {
    // Check if already authenticated this session
    if (sessionStorage.getItem("admin_auth") === "true") {
      isAuthenticated = true;
      loadMetrics();
    } else {
      loading = false;
    }

    // Cleanup on unmount
    return () => {
      if (refreshInterval) clearInterval(refreshInterval);
    };
  });

  // Auto-refresh when live tab is active
  $: if (activeTab === 'live' && isAuthenticated) {
    refreshInterval = setInterval(refreshLivePredictions, 30000); // Every 30 seconds
  } else {
    if (refreshInterval) {
      clearInterval(refreshInterval);
      refreshInterval = null;
    }
  }

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

  function toggleSort(column) {
    if (sortColumn === column) {
      sortDirection = sortDirection === "asc" ? "desc" : "asc";
    } else {
      sortColumn = column;
      sortDirection = column === "model" ? "asc" : "desc"; // Default asc for name, desc for numbers
    }
  }

  function getSortedModels(modelComparison) {
    const entries = Object.entries(modelComparison);

    return entries.sort(([nameA, statsA], [nameB, statsB]) => {
      let valueA, valueB;

      switch (sortColumn) {
        case "model":
          valueA = nameA.toLowerCase();
          valueB = nameB.toLowerCase();
          break;
        case "total":
          valueA = statsA.total;
          valueB = statsB.total;
          break;
        case "correct":
          valueA = statsA.correct;
          valueB = statsB.correct;
          break;
        case "accuracy":
        default:
          valueA = statsA.accuracy;
          valueB = statsB.accuracy;
          break;
      }

      if (sortDirection === "asc") {
        return valueA > valueB ? 1 : valueA < valueB ? -1 : 0;
      } else {
        return valueA < valueB ? 1 : valueA > valueB ? -1 : 0;
      }
    });
  }

  function getSortIcon(column) {
    if (sortColumn !== column) return "↕";
    return sortDirection === "asc" ? "↑" : "↓";
  }

  function formatDate(dateStr) {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  }

  function getProfitColor(profit) {
    if (profit > 0) return "text-emerald-400";
    if (profit < 0) return "text-red-400";
    return "text-slate-400";
  }

  function getResultStatus(prediction) {
    if (!prediction.actual_result) return { label: "Pending", color: "text-amber-400 bg-amber-400/10", icon: "⏳" };
    if (prediction.is_correct) return { label: "Correct", color: "text-emerald-400 bg-emerald-400/10", icon: "✓" };
    return { label: "Wrong", color: "text-red-400 bg-red-400/10", icon: "✗" };
  }

  function getConfidenceBar(confidence) {
    const width = Math.round(confidence * 100);
    let color = "bg-amber-500";
    if (confidence >= 0.7) color = "bg-emerald-500";
    else if (confidence >= 0.55) color = "bg-blue-500";
    return { width, color };
  }

  // Generate SVG path for accuracy trend chart
  function generateChartPath(data, width, height, padding = 20) {
    if (!data || data.length < 2) return "";

    const values = data.map(d => d.summary?.accuracy || 0);
    const minVal = Math.min(...values) * 0.9;
    const maxVal = Math.max(...values) * 1.1;
    const range = maxVal - minVal || 1;

    const xStep = (width - padding * 2) / (data.length - 1);

    const points = values.map((v, i) => {
      const x = padding + i * xStep;
      const y = height - padding - ((v - minVal) / range) * (height - padding * 2);
      return `${x},${y}`;
    });

    return `M ${points.join(" L ")}`;
  }

  function getChartPoints(data, width, height, padding = 20) {
    if (!data || data.length < 2) return [];

    const values = data.map(d => d.summary?.accuracy || 0);
    const minVal = Math.min(...values) * 0.9;
    const maxVal = Math.max(...values) * 1.1;
    const range = maxVal - minVal || 1;

    const xStep = (width - padding * 2) / (data.length - 1);

    return data.map((d, i) => {
      const v = d.summary?.accuracy || 0;
      return {
        x: padding + i * xStep,
        y: height - padding - ((v - minVal) / range) * (height - padding * 2),
        value: v,
        date: d.date
      };
    });
  }
</script>

<div class="space-y-6 page-enter">
  {#if !isAuthenticated}
    <!-- Login Form -->
    <div class="glass-card p-8 max-w-md mx-auto mt-20">
      <div class="text-center mb-6">
        <span class="text-4xl">🔐</span>
        <h1 class="text-2xl font-bold mt-4">Admin Access Required</h1>
        <p class="text-slate-400 mt-2">Enter password to view metrics</p>
      </div>

      <div class="space-y-4">
        <input
          type="password"
          bind:value={passwordInput}
          on:keydown={handleKeydown}
          placeholder="Enter password"
          class="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg focus:outline-none focus:border-accent text-white placeholder-slate-500"
        />

        {#if authError}
          <p class="text-red-400 text-sm text-center">{authError}</p>
        {/if}

        <button
          on:click={handleLogin}
          class="w-full px-4 py-3 bg-accent text-white rounded-lg font-medium hover:bg-accent/90 transition"
        >
          Access Dashboard
        </button>
      </div>

      <div class="mt-6 text-center">
        <Link to="/" class="text-slate-400 hover:text-white text-sm transition">
          ← Back to Home
        </Link>
      </div>
    </div>
  {:else}
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

    <!-- Tab Navigation -->
    <div class="flex gap-2 mt-4 border-b border-white/10 pb-0">
      <button
        on:click={() => activeTab = 'summary'}
        class="px-4 py-2 font-medium transition -mb-px {activeTab === 'summary' ? 'text-accent border-b-2 border-accent' : 'text-slate-400 hover:text-white'}"
      >
        📊 Current Metrics
      </button>
      <button
        on:click={() => activeTab = 'live'}
        class="px-4 py-2 font-medium transition -mb-px {activeTab === 'live' ? 'text-accent border-b-2 border-accent' : 'text-slate-400 hover:text-white'}"
      >
        🔴 Live Predictions
      </button>
      <button
        on:click={() => activeTab = 'history'}
        class="px-4 py-2 font-medium transition -mb-px {activeTab === 'history' ? 'text-accent border-b-2 border-accent' : 'text-slate-400 hover:text-white'}"
      >
        📈 Backtest History
      </button>
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
  {:else}

  <!-- Current Metrics Tab -->
  {#if activeTab === 'summary' && metrics}
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
          <span class="text-sm font-normal text-slate-400 ml-2">(click headers to sort)</span>
        </h2>

        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-white/10">
                <th
                  class="text-left py-3 px-4 font-medium text-slate-400 cursor-pointer hover:text-white transition select-none"
                  on:click={() => toggleSort("model")}
                >
                  Model <span class="text-xs ml-1">{getSortIcon("model")}</span>
                </th>
                <th
                  class="text-center py-3 px-4 font-medium text-slate-400 cursor-pointer hover:text-white transition select-none"
                  on:click={() => toggleSort("total")}
                >
                  Predictions <span class="text-xs ml-1">{getSortIcon("total")}</span>
                </th>
                <th
                  class="text-center py-3 px-4 font-medium text-slate-400 cursor-pointer hover:text-white transition select-none"
                  on:click={() => toggleSort("correct")}
                >
                  Correct <span class="text-xs ml-1">{getSortIcon("correct")}</span>
                </th>
                <th
                  class="text-right py-3 px-4 font-medium text-slate-400 cursor-pointer hover:text-white transition select-none"
                  on:click={() => toggleSort("accuracy")}
                >
                  Accuracy <span class="text-xs ml-1">{getSortIcon("accuracy")}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {#each getSortedModels(metrics.model_comparison) as [model, stats]}
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

  <!-- Live Predictions Tab -->
  {#if activeTab === 'live'}
    {#if livePredictions && livePredictions.length > 0}
      <!-- Live Stats Summary -->
      {@const completed = livePredictions.filter(p => p.actual_result)}
      {@const correct = completed.filter(p => p.is_correct)}
      {@const pending = livePredictions.filter(p => !p.actual_result)}

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="glass-card p-4">
          <div class="text-slate-400 text-sm font-medium mb-2">Total Predictions</div>
          <div class="text-3xl font-bold text-blue-400">{livePredictions.length}</div>
          <div class="text-xs text-slate-500 mt-2">In database</div>
        </div>

        <div class="glass-card p-4">
          <div class="text-slate-400 text-sm font-medium mb-2">Pending Results</div>
          <div class="text-3xl font-bold text-amber-400">{pending.length}</div>
          <div class="text-xs text-slate-500 mt-2">Awaiting match outcomes</div>
        </div>

        <div class="glass-card p-4">
          <div class="text-slate-400 text-sm font-medium mb-2">Completed</div>
          <div class="text-3xl font-bold text-slate-300">{completed.length}</div>
          <div class="text-xs text-slate-500 mt-2">Results recorded</div>
        </div>

        <div class="glass-card p-4">
          <div class="text-slate-400 text-sm font-medium mb-2">Live Accuracy</div>
          <div class={`text-3xl font-bold ${completed.length > 0 ? getAccuracyColor(correct.length / completed.length) : 'text-slate-500'}`}>
            {completed.length > 0 ? ((correct.length / completed.length) * 100).toFixed(1) : '—'}%
          </div>
          <div class="text-xs text-slate-500 mt-2">
            {correct.length} / {completed.length} correct
          </div>
        </div>
      </div>

      <!-- Recent Predictions Table -->
      <div class="glass-card p-6">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-bold flex items-center gap-2">
            <span>🔴</span> Recent Predictions
            <span class="text-sm font-normal text-slate-400 ml-2">(auto-refreshes every 30s)</span>
          </h2>
          <button
            on:click={refreshLivePredictions}
            class="px-3 py-1 bg-white/10 hover:bg-white/20 rounded text-sm transition"
          >
            🔄 Refresh
          </button>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-white/10">
                <th class="text-left py-3 px-4 font-medium text-slate-400">Match</th>
                <th class="text-center py-3 px-4 font-medium text-slate-400">League</th>
                <th class="text-center py-3 px-4 font-medium text-slate-400">Prediction</th>
                <th class="text-center py-3 px-4 font-medium text-slate-400">Confidence</th>
                <th class="text-center py-3 px-4 font-medium text-slate-400">Actual</th>
                <th class="text-center py-3 px-4 font-medium text-slate-400">Status</th>
                <th class="text-right py-3 px-4 font-medium text-slate-400">Date</th>
              </tr>
            </thead>
            <tbody>
              {#each livePredictions as prediction}
                {@const status = getResultStatus(prediction)}
                {@const conf = getConfidenceBar(prediction.confidence || 0)}
                <tr class="border-t border-white/5 hover:bg-white/5 transition">
                  <td class="py-3 px-4">
                    <div class="font-medium">{prediction.home_team}</div>
                    <div class="text-slate-400 text-xs">vs {prediction.away_team}</div>
                  </td>
                  <td class="py-3 px-4 text-center text-slate-400 text-xs">
                    {prediction.league_name || '—'}
                  </td>
                  <td class="py-3 px-4 text-center font-medium">
                    {prediction.predicted_result || '—'}
                  </td>
                  <td class="py-3 px-4">
                    <div class="flex items-center gap-2">
                      <div class="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                        <div class="{conf.color} h-full rounded-full" style="width: {conf.width}%"></div>
                      </div>
                      <span class="text-xs text-slate-400 w-10 text-right">{conf.width}%</span>
                    </div>
                  </td>
                  <td class="py-3 px-4 text-center font-medium">
                    {prediction.actual_result || '—'}
                  </td>
                  <td class="py-3 px-4 text-center">
                    <span class="px-2 py-1 rounded text-xs font-medium {status.color}">
                      {status.icon} {status.label}
                    </span>
                  </td>
                  <td class="py-3 px-4 text-right text-slate-400 text-xs">
                    {formatDate(prediction.match_date || prediction.created_at)}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    {:else}
      <div class="glass-card p-8 text-center">
        <div class="text-6xl mb-4">🔴</div>
        <h2 class="text-xl font-bold mb-2">No Live Predictions Yet</h2>
        <p class="text-slate-400 mb-4">
          Predictions will appear here as users request them through the app.
        </p>
        <p class="text-sm text-slate-500">
          Each prediction is logged to the database with full model breakdown for analysis.
        </p>
      </div>
    {/if}
  {/if}

  <!-- Backtest History Tab -->
  {#if activeTab === 'history'}
    {#if backtestHistory && backtestHistory.length > 0}
      <!-- Backtest Summary Cards -->
      {#if backtestSummary}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div class="glass-card p-4">
            <div class="text-slate-400 text-sm font-medium mb-2">Total Weeks Tracked</div>
            <div class="text-3xl font-bold text-blue-400">
              {backtestSummary.total_weeks}
            </div>
            <div class="text-xs text-slate-500 mt-2">Weekly backtest runs</div>
          </div>

          <div class="glass-card p-4">
            <div class="text-slate-400 text-sm font-medium mb-2">Avg Weekly Accuracy</div>
            <div class={`text-3xl font-bold ${getAccuracyColor(backtestSummary.avg_accuracy / 100)}`}>
              {backtestSummary.avg_accuracy.toFixed(1)}%
            </div>
            <div class="text-xs text-slate-500 mt-2">Across all weeks</div>
          </div>

          <div class="glass-card p-4">
            <div class="text-slate-400 text-sm font-medium mb-2">Total Profit</div>
            <div class={`text-3xl font-bold ${getProfitColor(backtestSummary.total_profit)}`}>
              ${backtestSummary.total_profit.toFixed(2)}
            </div>
            <div class="text-xs text-slate-500 mt-2">Simulated betting profit</div>
          </div>

          <div class="glass-card p-4">
            <div class="text-slate-400 text-sm font-medium mb-2">Best Week</div>
            {#if backtestSummary.best_week}
              <div class="text-3xl font-bold text-emerald-400">
                {backtestSummary.best_week.summary?.accuracy?.toFixed(1) || 'N/A'}%
              </div>
              <div class="text-xs text-slate-500 mt-2">
                {formatDate(backtestSummary.best_week.date)}
              </div>
            {:else}
              <div class="text-3xl font-bold text-slate-500">N/A</div>
            {/if}
          </div>
        </div>
      {/if}

      <!-- Backtest History Table -->
      <div class="glass-card p-6">
        <h2 class="text-xl font-bold mb-4 flex items-center gap-2">
          <span>📅</span> Weekly Backtest Results
          <span class="text-sm font-normal text-slate-400 ml-2">(last 52 weeks)</span>
        </h2>

        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-white/10">
                <th class="text-left py-3 px-4 font-medium text-slate-400">Date</th>
                <th class="text-center py-3 px-4 font-medium text-slate-400">Matches</th>
                <th class="text-center py-3 px-4 font-medium text-slate-400">Correct</th>
                <th class="text-center py-3 px-4 font-medium text-slate-400">Accuracy</th>
                <th class="text-center py-3 px-4 font-medium text-slate-400">ROI</th>
                <th class="text-right py-3 px-4 font-medium text-slate-400">Profit</th>
              </tr>
            </thead>
            <tbody>
              {#each [...backtestHistory].reverse() as week}
                <tr class="border-t border-white/5 hover:bg-white/5 transition">
                  <td class="py-3 px-4 font-medium">{formatDate(week.date)}</td>
                  <td class="py-3 px-4 text-center text-slate-300">{week.summary?.evaluated || week.sample_size || 0}</td>
                  <td class="py-3 px-4 text-center text-slate-300">{week.summary?.correct || 0}</td>
                  <td class="py-3 px-4 text-center">
                    <span class={`font-bold ${getAccuracyColor((week.summary?.accuracy || 0) / 100)}`}>
                      {(week.summary?.accuracy || 0).toFixed(1)}%
                    </span>
                  </td>
                  <td class="py-3 px-4 text-center">
                    <span class={`font-medium ${getProfitColor(week.summary?.roi || 0)}`}>
                      {(week.summary?.roi || 0).toFixed(1)}%
                    </span>
                  </td>
                  <td class="py-3 px-4 text-right">
                    <span class={`font-bold ${getProfitColor(week.summary?.profit || 0)}`}>
                      ${(week.summary?.profit || 0).toFixed(2)}
                    </span>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Accuracy Trend Chart -->
      <div class="glass-card p-6">
        <h2 class="text-xl font-bold mb-4 flex items-center gap-2">
          <span>📈</span> Accuracy Trend
        </h2>
        {@const chartWidth = 700}
        {@const chartHeight = 200}
        {@const chartData = [...backtestHistory].reverse().slice(-12)}
        {@const points = getChartPoints(chartData, chartWidth, chartHeight)}

        {#if points.length >= 2}
          <div class="overflow-x-auto">
            <svg width="{chartWidth}" height="{chartHeight}" class="w-full max-w-full" viewBox="0 0 {chartWidth} {chartHeight}">
              <!-- Grid lines -->
              <line x1="20" y1="{chartHeight - 20}" x2="{chartWidth - 20}" y2="{chartHeight - 20}" stroke="rgba(255,255,255,0.1)" />
              <line x1="20" y1="{chartHeight / 2}" x2="{chartWidth - 20}" y2="{chartHeight / 2}" stroke="rgba(255,255,255,0.05)" stroke-dasharray="4" />
              <line x1="20" y1="20" x2="{chartWidth - 20}" y2="20" stroke="rgba(255,255,255,0.05)" stroke-dasharray="4" />

              <!-- Gradient area fill -->
              <defs>
                <linearGradient id="areaGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" style="stop-color: rgb(52, 211, 153); stop-opacity: 0.3" />
                  <stop offset="100%" style="stop-color: rgb(52, 211, 153); stop-opacity: 0.05" />
                </linearGradient>
              </defs>

              <!-- Area fill -->
              <path
                d="{generateChartPath(chartData, chartWidth, chartHeight)} L {points[points.length - 1]?.x || 0},{chartHeight - 20} L 20,{chartHeight - 20} Z"
                fill="url(#areaGradient)"
              />

              <!-- Line -->
              <path
                d="{generateChartPath(chartData, chartWidth, chartHeight)}"
                fill="none"
                stroke="rgb(52, 211, 153)"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              />

              <!-- Data points -->
              {#each points as point, i}
                <circle
                  cx="{point.x}"
                  cy="{point.y}"
                  r="4"
                  fill="rgb(52, 211, 153)"
                  class="hover:r-6 transition-all cursor-pointer"
                >
                  <title>{formatDate(point.date)}: {point.value.toFixed(1)}%</title>
                </circle>
              {/each}

              <!-- Y-axis labels -->
              <text x="15" y="25" fill="rgba(255,255,255,0.5)" font-size="10" text-anchor="end">High</text>
              <text x="15" y="{chartHeight - 15}" fill="rgba(255,255,255,0.5)" font-size="10" text-anchor="end">Low</text>
            </svg>
          </div>

          <!-- Chart legend -->
          <div class="flex justify-between mt-4 text-xs text-slate-500">
            <span>{formatDate(chartData[0]?.date)}</span>
            <span class="text-emerald-400">Last 12 weeks accuracy trend</span>
            <span>{formatDate(chartData[chartData.length - 1]?.date)}</span>
          </div>
        {:else}
          <div class="h-48 flex items-center justify-center bg-white/5 rounded-lg">
            <div class="text-center text-slate-400">
              <div class="text-4xl mb-2">📊</div>
              <p>Need more data for trend chart</p>
              <p class="text-xs text-slate-500 mt-1">At least 2 weeks of backtest data required</p>
            </div>
          </div>
        {/if}
      </div>
    {:else}
      <div class="glass-card p-8 text-center">
        <div class="text-6xl mb-4">📅</div>
        <h2 class="text-xl font-bold mb-2">No Backtest History Yet</h2>
        <p class="text-slate-400 mb-4">
          Backtest results will appear here after the weekly training workflow runs.
        </p>
        <p class="text-sm text-slate-500">
          The workflow runs automatically every Monday at 3 AM UTC, or can be triggered manually from GitHub Actions.
        </p>
      </div>
    {/if}
  {/if}

  {/if}
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
