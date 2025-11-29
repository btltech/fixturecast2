<script>
  import { onMount } from "svelte";
  import { ML_API_URL, BACKEND_API_URL } from "../config.js";

  let stats = null;
  let backtestHistory = null;
  let loading = true;
  let error = null;
  let apiAvailable = false;

  const modelInfo = {
    gbdt: {
      name: "Gradient Boosting",
      description: "Tree-based ensemble for recent form analysis",
      icon: "🌳",
      color: "from-green-500 to-emerald-600",
    },
    catboost: {
      name: "CatBoost",
      description: "Advanced gradient boosting with categorical features",
      icon: "🐱",
      color: "from-orange-500 to-red-600",
    },
    poisson: {
      name: "Poisson Regression",
      description: "Statistical model for goal distribution",
      icon: "📊",
      color: "from-blue-500 to-cyan-600",
    },
    transformer: {
      name: "Transformer",
      description: "Attention-based sequence modeling",
      icon: "🔄",
      color: "from-purple-500 to-pink-600",
    },
    lstm: {
      name: "LSTM Neural Network",
      description: "Long short-term memory for trend analysis",
      icon: "🧠",
      color: "from-indigo-500 to-blue-600",
    },
    gnn: {
      name: "Graph Neural Network",
      description: "League context and team relationships",
      icon: "🕸️",
      color: "from-teal-500 to-green-600",
    },
    bayesian: {
      name: "Bayesian Model",
      description: "Probabilistic inference with betting odds",
      icon: "🎲",
      color: "from-yellow-500 to-orange-600",
    },
    elo: {
      name: "Elo/Glicko Rating",
      description: "Long-term team strength rating system",
      icon: "⚖️",
      color: "from-gray-500 to-slate-600",
    },
    monte_carlo: {
      name: "Monte Carlo Simulation",
      description: "Scoreline probability distribution",
      icon: "🎰",
      color: "from-red-500 to-pink-600",
    },
    calibration: {
      name: "Calibration Model",
      description: "Probability adjustment and sharpening",
      icon: "🎯",
      color: "from-cyan-500 to-blue-600",
    },
    meta: {
      name: "Meta Model",
      description: "Stacking ensemble learner",
      icon: "🏆",
      color: "from-amber-500 to-yellow-600",
    },
  };

  // All models in our ensemble
  const allModels = Object.entries(modelInfo);

  onMount(async () => {
    try {
      // Fetch live model stats
      const response = await fetch(`${ML_API_URL}/api/model-stats`);
      if (response.ok) {
        stats = await response.json();
        apiAvailable = true;
      } else {
        apiAvailable = false;
      }

      // Fetch backtest history
      const historyResponse = await fetch(
        `${BACKEND_API_URL}/api/metrics/backtest-history`,
      );
      if (historyResponse.ok) {
        backtestHistory = await historyResponse.json();
      }
    } catch (err) {
      apiAvailable = false;
    } finally {
      loading = false;
    }
  });
</script>

<div class="space-y-6">
  <div class="glass-card p-6">
    <h1 class="text-2xl md:text-3xl font-bold mb-2">ML Ensemble System</h1>
    <p class="text-slate-400 text-sm md:text-base">
      Our prediction engine uses an ensemble of 11 specialized machine learning
      models
    </p>
    <p class="text-xs text-amber-400 mt-2">
      🆕 Launched November 25, 2025 - Performance tracking begins after first week
    </p>
  </div>

  {#if loading}
    <div class="glass-card p-12 text-center">
      <div
        class="inline-block w-12 h-12 border-4 border-accent border-t-transparent rounded-full animate-spin"
      ></div>
      <p class="mt-4 text-slate-400">Loading model information...</p>
    </div>
  {:else}
    <!-- Weekly Performance Section (Backtest Results) - Only show if we have real data -->
    {#if backtestHistory && backtestHistory.history && backtestHistory.history.length > 0}
      <div class="glass-card p-6 border border-green-500/30">
        <div class="flex items-center justify-between mb-4">
          <div>
            <h2 class="text-xl font-bold text-green-400">
              ✅ Weekly Performance
            </h2>
            <p class="text-xs text-slate-400">
              Verified backtest results on completed matches
            </p>
          </div>
          <div class="text-right">
            <div class="text-2xl font-bold text-white">
              {backtestHistory.summary.avg_accuracy.toFixed(1)}%
            </div>
            <div class="text-xs text-slate-400">Avg Accuracy</div>
          </div>
        </div>

        <div class="space-y-3">
          {#each backtestHistory.history.slice().reverse().slice(0, 3) as week}
            <div
              class="bg-white/5 rounded p-3 flex justify-between items-center"
            >
              <div>
                <div class="font-bold text-sm">
                  Week of {new Date(week.date).toLocaleDateString()}
                </div>
                <div class="text-xs text-slate-400">
                  {week.summary.evaluated} matches evaluated
                </div>
              </div>
              <div class="text-right">
                <div
                  class="font-bold {week.summary.accuracy >= 40
                    ? 'text-green-400'
                    : 'text-amber-400'}"
                >
                  {week.summary.accuracy.toFixed(1)}%
                </div>
              </div>
            </div>
          {/each}
        </div>
      </div>
    {:else}
      <!-- No backtest data yet - App just launched -->
      <div class="glass-card p-6 border border-amber-500/30">
        <div class="flex items-start gap-3">
          <span class="text-2xl">📊</span>
          <div>
            <h3 class="font-bold text-amber-400">
              Performance Tracking Starting Soon
            </h3>
            <p class="text-sm text-slate-400 mt-1">
              FixtureCast launched on November 25, 2025. Weekly performance backtests
              will begin after our first full week of predictions. Check back soon for
              verified accuracy metrics on completed matches.
            </p>
            <p class="text-xs text-slate-500 mt-2">
              First backtest scheduled: Week of December 2, 2025
            </p>
          </div>
        </div>
      </div>
    {/if}

    {#if apiAvailable && stats}
      <!-- Model Info - Only show verified data -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
        <div class="glass-card p-6">
          <div class="text-sm text-slate-400 mb-2">Active Models</div>
          <div class="text-3xl md:text-4xl font-bold text-green-400">
            {stats.models.filter((m) => m.status === "active").length}
          </div>
          <div class="text-xs text-slate-500 mt-1">
            Contributing to ensemble predictions
          </div>
        </div>
        <div class="glass-card p-6">
          <div class="text-sm text-slate-400 mb-2">Tracking Since</div>
          <div class="text-xl md:text-2xl font-bold">
            {#if stats.tracking_since}
              {new Date(stats.tracking_since).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
            {:else}
              Nov 25, 2025
            {/if}
          </div>
          <div class="text-xs text-slate-500 mt-1">
            App launch date
          </div>
        </div>
      </div>

      {#if stats.note}
        <div class="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
          <p class="text-sm text-blue-300">💡 {stats.note}</p>
        </div>
      {/if}

      <!-- Individual Model Stats from API -->
      <div class="glass-card p-4 md:p-6">
        <h2 class="text-xl md:text-2xl font-bold mb-6">
          Individual Model Performance
        </h2>
        <div class="space-y-4">
          {#each stats.models as model}
            {@const info = modelInfo[model.name] || {
              name: model.full_name || model.name,
              description: model.description || "Model",
              icon: "🤖",
              color: "from-gray-500 to-slate-600",
            }}
            <div
              class="bg-white/5 rounded-lg p-4 md:p-6 hover:bg-white/10 transition-all {model.status ===
              'auxiliary'
                ? 'opacity-60'
                : ''}"
            >
              <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-3">
                  <div
                    class="w-10 h-10 md:w-12 md:h-12 rounded-lg bg-gradient-to-br {info.color} flex items-center justify-center text-xl md:text-2xl"
                  >
                    {info.icon}
                  </div>
                  <div>
                    <div
                      class="font-bold text-base md:text-lg flex items-center gap-2"
                    >
                      {model.full_name || info.name}
                      {#if model.status === "auxiliary"}
                        <span class="text-xs bg-slate-600 px-2 py-0.5 rounded"
                          >Auxiliary</span
                        >
                      {/if}
                    </div>
                    <div class="text-xs md:text-sm text-slate-400">
                      {model.description || info.description}
                    </div>
                  </div>
                </div>
                <div class="text-right">
                  <div class="text-xl md:text-2xl font-bold text-accent">
                    {(model.weight * 100).toFixed(0)}%
                  </div>
                  <div class="text-xs text-slate-400">Weight</div>
                </div>
              </div>

              <div class="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <div class="text-slate-400 text-xs">Type</div>
                  <div class="font-bold text-xs">{model.type || "ML"}</div>
                </div>
                <div>
                  <div class="text-slate-400 text-xs">Status</div>
                  <div class="font-bold text-xs {model.status === 'active' ? 'text-green-400' : 'text-slate-400'}">
                    {model.status === 'active' ? '● Active' : '○ Auxiliary'}
                  </div>
                </div>
              </div>

              <div class="mt-4 bg-white/10 h-2 rounded-full overflow-hidden">
                <div
                  class="bg-gradient-to-r {info.color} h-full rounded-full transition-all"
                  style="width: {model.weight * 100}%"
                ></div>
              </div>
            </div>
          {/each}
        </div>
      </div>
    {:else}
      <!-- No stats available - Show model descriptions only -->
      <div class="glass-card p-4 md:p-6 border border-amber-500/30">
        <div class="flex items-start gap-3 mb-4">
          <span class="text-2xl">📊</span>
          <div>
            <h3 class="font-bold text-amber-400">
              Performance Tracking Coming Soon
            </h3>
            <p class="text-sm text-slate-400 mt-1">
              Live accuracy metrics will be available once the system has
              processed enough predictions to generate meaningful statistics.
            </p>
          </div>
        </div>
      </div>

      <!-- Model Overview Cards -->
      <div class="glass-card p-4 md:p-6">
        <h2 class="text-xl md:text-2xl font-bold mb-2">
          Our 11-Model Ensemble
        </h2>
        <p class="text-slate-400 text-sm mb-6">
          Each model specializes in different aspects of match prediction
        </p>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {#each allModels as [key, info]}
            <div
              class="bg-white/5 rounded-lg p-4 hover:bg-white/10 transition-all"
            >
              <div class="flex items-center gap-3 mb-3">
                <div
                  class="w-10 h-10 rounded-lg bg-gradient-to-br {info.color} flex items-center justify-center text-xl flex-shrink-0"
                >
                  {info.icon}
                </div>
                <div class="font-bold text-sm">{info.name}</div>
              </div>
              <p class="text-xs text-slate-400 leading-relaxed">
                {info.description}
              </p>
            </div>
          {/each}
        </div>
      </div>

      <!-- How It Works -->
      <div class="glass-card p-4 md:p-6">
        <h3 class="text-lg md:text-xl font-bold mb-4">
          How Ensemble Prediction Works
        </h3>
        <div class="space-y-4 text-sm text-slate-300">
          <div class="flex gap-3">
            <span class="text-accent font-bold">1.</span>
            <p>
              Each model independently analyzes the match using its specialized
              approach
            </p>
          </div>
          <div class="flex gap-3">
            <span class="text-accent font-bold">2.</span>
            <p>
              Models are weighted based on historical accuracy (learned weights)
            </p>
          </div>
          <div class="flex gap-3">
            <span class="text-accent font-bold">3.</span>
            <p>
              A meta-model combines predictions using stacking ensemble
              technique
            </p>
          </div>
          <div class="flex gap-3">
            <span class="text-accent font-bold">4.</span>
            <p>
              Calibration adjusts final probabilities for optimal reliability
            </p>
          </div>
        </div>
      </div>
    {/if}
  {/if}
</div>
