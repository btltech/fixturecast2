<script>
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";

  let metrics = null;
  let loading = true;
  let error = null;
  const BACKEND_API = import.meta.env.VITE_BACKEND_API || "http://localhost:8000";

  // Password protection
  const ADMIN_PASSWORD = import.meta.env.VITE_ADMIN_PASSWORD || "fixturecast2025";
  let isAuthenticated = false;
  let passwordInput = "";
  let authError = "";

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
      const res = await fetch(`${BACKEND_API}/api/metrics/summary`);
      if (!res.ok) throw new Error("Failed to load metrics");
      metrics = await res.json();
    } catch (e) {
      error = e.message;
      console.error("Error loading metrics:", e);
    } finally {
      loading = false;
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
