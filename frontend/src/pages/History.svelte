<script>
  import { onMount } from "svelte";
  import { Link } from "svelte-routing";
  import { predictionHistory, clearHistory } from "../services/historyStore.js";

  // Use reactive auto-subscription ($ prefix) - automatically unsubscribes
  $: history = $predictionHistory || [];
</script>

<div class="space-y-6">
  <div class="glass-card p-6">
    <div class="flex justify-between items-center">
      <div>
        <h1 class="text-3xl font-bold mb-2">Prediction History</h1>
        <p class="text-slate-400">
          Your recently viewed predictions ({history.length}/{50})
        </p>
      </div>
      {#if history.length > 0}
        <button
          on:click={clearHistory}
          class="px-4 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-all"
        >
          Clear All
        </button>
      {/if}
    </div>
  </div>

  {#if history.length === 0}
    <div class="glass-card p-12 text-center">
      <div class="text-6xl mb-4">📊</div>
      <p class="text-slate-400">
        No prediction history yet. View some predictions to see them here!
      </p>
      <Link
        to="/predictions"
        class="inline-block mt-4 px-6 py-3 bg-accent text-white rounded-lg hover:bg-accent/80 transition-all"
      >
        View Predictions
      </Link>
    </div>
  {:else}
    <div class="space-y-4">
      {#each history as item}
        <div class="glass-card p-6 hover:bg-white/5 transition-all">
          <div class="flex items-center justify-between mb-4">
            <div class="text-sm text-slate-400">
              Viewed: {new Date(item.viewed_at).toLocaleDateString("en-US", {
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </div>
            <Link
              to={`/prediction/${item.fixture_id}?league=${item.league_id || 39}${item.season ? `&season=${item.season}` : ""}`}
              class="text-sm text-accent hover:underline"
            >
              View Again →
            </Link>
          </div>

          <div class="grid grid-cols-[1fr_auto_1fr] gap-4 items-center">
            <div class="text-right">
              <div class="font-bold text-lg">{item.home_team}</div>
              {#if item.home_win_prob}
                <div class="text-sm text-slate-400">
                  {(item.home_win_prob * 100).toFixed(0)}% win prob
                </div>
              {/if}
            </div>

            <div class="flex items-center gap-2">
              <div class="px-4 py-2 bg-white/10 rounded-lg text-sm font-mono">
                {item.predicted_score || "vs"}
              </div>
            </div>

            <div class="text-left">
              <div class="font-bold text-lg">{item.away_team}</div>
              {#if item.away_win_prob}
                <div class="text-sm text-slate-400">
                  {(item.away_win_prob * 100).toFixed(0)}% win prob
                </div>
              {/if}
            </div>
          </div>

          {#if item.confidence}
            <div class="mt-4 flex items-center gap-2">
              <span class="text-xs text-slate-400">Confidence:</span>
              <div class="flex-1 bg-white/10 h-2 rounded-full overflow-hidden">
                <div
                  class="bg-accent h-full rounded-full"
                  style="width: {item.confidence * 100}%"
                ></div>
              </div>
              <span class="text-xs font-bold"
                >{(item.confidence * 100).toFixed(0)}%</span
              >
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>
