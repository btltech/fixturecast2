<script>
  // Compare Panel Component
  // Floating panel that shows when fixtures are selected for comparison
  import { Link } from "svelte-routing";
  import { onDestroy } from "svelte";
  import { compareStore } from "../services/compareStore.js";
  import ConfidenceBadge from "./ConfidenceBadge.svelte";
  import SkeletonLoader from "./SkeletonLoader.svelte";
  import { ML_API_URL } from "../config.js";

  let predictions = [null, null];
  let loading = [false, false];

  // Use reactive auto-subscription ($ prefix) - automatically unsubscribes
  $: isOpen = $compareStore?.isOpen || false;
  $: compareFixtures = $compareStore?.fixtures || [];
  
  // React to fixture changes to load predictions
  $: if (compareFixtures[0] && !predictions[0]) {
    loadPrediction(compareFixtures[0], 0);
  }
  $: if (compareFixtures[1] && !predictions[1]) {
    loadPrediction(compareFixtures[1], 1);
  }
  // Clear predictions when removed
  $: if (!compareFixtures[0]) predictions[0] = null;
  $: if (!compareFixtures[1]) predictions[1] = null;

  async function loadPrediction(fixtureId, index) {
    if (!fixtureId || predictions[index]?.fixture_id === fixtureId) return;
    
    loading[index] = true;
    loading = [...loading];
    
    try {
      const res = await fetch(
        `${ML_API_URL}/api/prediction/${fixtureId}?league=39&season=2025`
      );
      if (res.ok) {
        const data = await res.json();
        data.fixture_id = fixtureId;
        predictions[index] = data;
        predictions = [...predictions];
      }
    } catch (e) {
      console.error(`Error loading prediction ${fixtureId}:`, e);
    } finally {
      loading[index] = false;
      loading = [...loading];
    }
  }

  function closePanel() {
    compareStore.close();
    predictions = [null, null];
  }

  function openPanel() {
    compareStore.openPanel();
  }

  function removeFixture(index) {
    const fixtureId = compareFixtures[index];
    if (fixtureId) {
      compareStore.removeFixture(fixtureId);
      predictions[index] = null;
      predictions = [...predictions];
    }
  }

  function getMaxProb(pred) {
    if (!pred?.prediction) return 0;
    return Math.max(
      pred.prediction.home_win_prob,
      pred.prediction.draw_prob,
      pred.prediction.away_win_prob
    );
  }

  function getOutcome(pred) {
    if (!pred?.prediction) return { label: "-", color: "text-slate-400" };
    const p = pred.prediction;
    if (p.home_win_prob > p.away_win_prob && p.home_win_prob > p.draw_prob) {
      return { label: "Home Win", color: "text-emerald-400" };
    } else if (p.away_win_prob > p.home_win_prob && p.away_win_prob > p.draw_prob) {
      return { label: "Away Win", color: "text-rose-400" };
    }
    return { label: "Draw", color: "text-slate-400" };
  }
</script>

<!-- Floating Compare Button (shows when fixtures selected but panel closed) -->
{#if compareFixtures.length > 0 && !isOpen}
  <button
    on:click={openPanel}
    class="fixed bottom-20 md:bottom-6 right-4 z-40 bg-accent text-white px-4 py-3 rounded-full shadow-lg shadow-accent/30 flex items-center gap-2 hover:bg-accent/90 transition-all animate-bounce-in"
  >
    <span>⚖️</span>
    <span class="font-bold">Compare ({compareFixtures.length})</span>
  </button>
{/if}

<!-- Compare Modal/Panel -->
{#if isOpen}
  <div class="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
    <!-- Backdrop -->
    <button 
      class="absolute inset-0 bg-black/70 backdrop-blur-sm"
      on:click={closePanel}
      aria-label="Close compare panel"
    ></button>
    
    <!-- Panel -->
    <div class="relative w-full max-w-4xl max-h-[85vh] overflow-y-auto bg-slate-900 rounded-t-3xl sm:rounded-2xl shadow-2xl border border-white/10 m-0 sm:m-4">
      <!-- Handle for mobile -->
      <div class="sm:hidden w-12 h-1 bg-slate-600 rounded-full mx-auto mt-3"></div>
      
      <!-- Header -->
      <div class="sticky top-0 bg-slate-900/95 backdrop-blur-sm border-b border-white/10 p-4 flex items-center justify-between">
        <h2 class="text-lg font-bold flex items-center gap-2">
          <span>⚖️</span> Compare Predictions
        </h2>
        <button 
          on:click={closePanel}
          class="p-2 hover:bg-white/10 rounded-lg transition-colors"
          aria-label="Close"
        >
          ✕
        </button>
      </div>

      <!-- Content -->
      <div class="p-4">
        {#if compareFixtures.length === 0}
          <div class="text-center py-12 text-slate-400">
            <div class="text-4xl mb-3">📊</div>
            <p>No fixtures selected for comparison</p>
            <p class="text-sm mt-2">Click "⚖️ Compare" on fixture cards</p>
          </div>
        {:else}
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {#each [0, 1] as index}
              <div class="glass-card p-4 relative min-h-[300px] {!predictions[index] && !loading[index] && !compareFixtures[index] ? 'border-dashed border-2 border-white/20 flex items-center justify-center' : ''}">
                {#if loading[index]}
                  <SkeletonLoader type="prediction" />
                {:else if predictions[index]}
                  {@const pred = predictions[index]}
                  {@const outcome = getOutcome(pred)}
                  
                  <!-- Remove button -->
                  <button 
                    on:click={() => removeFixture(index)}
                    class="absolute top-2 right-2 p-1.5 hover:bg-white/10 rounded-lg text-slate-400 hover:text-white transition-colors z-10"
                    aria-label="Remove from compare"
                  >
                    ✕
                  </button>

                  <!-- Teams -->
                  <div class="flex items-center justify-between mb-4">
                    <div class="flex-1 text-center">
                      <img 
                        src={pred.fixture_details?.teams?.home?.logo} 
                        alt="" 
                        class="w-12 h-12 mx-auto mb-1"
                      />
                      <div class="text-sm font-medium truncate px-1">
                        {pred.fixture_details?.teams?.home?.name || "Home"}
                      </div>
                    </div>
                    <div class="px-2 text-slate-500 text-sm">vs</div>
                    <div class="flex-1 text-center">
                      <img 
                        src={pred.fixture_details?.teams?.away?.logo} 
                        alt="" 
                        class="w-12 h-12 mx-auto mb-1"
                      />
                      <div class="text-sm font-medium truncate px-1">
                        {pred.fixture_details?.teams?.away?.name || "Away"}
                      </div>
                    </div>
                  </div>

                  <!-- Predicted Score -->
                  <div class="text-center mb-4">
                    <div class="text-3xl font-bold font-mono">
                      {pred.prediction?.predicted_scoreline || "? - ?"}
                    </div>
                    <div class="text-xs text-slate-400 mt-1">Predicted Score</div>
                  </div>

                  <!-- Outcome & Confidence -->
                  <div class="flex items-center justify-between mb-4">
                    <span class="text-sm {outcome.color} font-medium">{outcome.label}</span>
                    <ConfidenceBadge confidence={getMaxProb(pred)} size="sm" />
                  </div>

                  <!-- Probability Bars -->
                  <div class="space-y-2 text-xs">
                    <div class="flex items-center gap-2">
                      <span class="w-8 text-slate-400">H</span>
                      <div class="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                        <div 
                          class="h-full bg-emerald-500 rounded-full transition-all"
                          style="width: {(pred.prediction?.home_win_prob || 0) * 100}%"
                        ></div>
                      </div>
                      <span class="w-10 text-right font-mono">
                        {((pred.prediction?.home_win_prob || 0) * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div class="flex items-center gap-2">
                      <span class="w-8 text-slate-400">D</span>
                      <div class="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                        <div 
                          class="h-full bg-slate-500 rounded-full transition-all"
                          style="width: {(pred.prediction?.draw_prob || 0) * 100}%"
                        ></div>
                      </div>
                      <span class="w-10 text-right font-mono">
                        {((pred.prediction?.draw_prob || 0) * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div class="flex items-center gap-2">
                      <span class="w-8 text-slate-400">A</span>
                      <div class="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                        <div 
                          class="h-full bg-rose-500 rounded-full transition-all"
                          style="width: {(pred.prediction?.away_win_prob || 0) * 100}%"
                        ></div>
                      </div>
                      <span class="w-10 text-right font-mono">
                        {((pred.prediction?.away_win_prob || 0) * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>

                  <!-- Additional Stats -->
                  <div class="mt-4 pt-4 border-t border-white/10 grid grid-cols-2 gap-3 text-xs">
                    <div class="bg-white/5 rounded-lg p-2 text-center">
                      <div class="text-slate-400">BTTS</div>
                      <div class="font-bold">{((pred.prediction?.btts_prob || 0) * 100).toFixed(0)}%</div>
                    </div>
                    <div class="bg-white/5 rounded-lg p-2 text-center">
                      <div class="text-slate-400">Over 2.5</div>
                      <div class="font-bold">{((pred.prediction?.over25_prob || 0) * 100).toFixed(0)}%</div>
                    </div>
                  </div>

                  <!-- View Full -->
                  <Link 
                    to={`/prediction/${compareFixtures[index]}`}
                    class="block mt-4 text-center text-accent text-sm hover:underline"
                    on:click={closePanel}
                  >
                    View Full Analysis →
                  </Link>
                {:else}
                  <!-- Empty slot -->
                  <div class="text-center py-8 text-slate-400">
                    <div class="text-3xl mb-2">➕</div>
                    <p class="text-sm">Add a fixture to compare</p>
                  </div>
                {/if}
              </div>
            {/each}
          </div>

          <!-- Comparison Summary -->
          {#if predictions[0] && predictions[1]}
            <div class="mt-6 glass-card p-4">
              <h3 class="font-bold mb-3 flex items-center gap-2">
                <span>📊</span> Quick Comparison
              </h3>
              
              <div class="overflow-x-auto">
                <table class="w-full text-sm">
                  <thead>
                    <tr class="text-slate-400 text-xs">
                      <th class="text-left py-2 font-medium">Fixture 1</th>
                      <th class="text-center py-2 font-medium">Metric</th>
                      <th class="text-right py-2 font-medium">Fixture 2</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr class="border-t border-white/5">
                      <td class="py-2 {getMaxProb(predictions[0]) > getMaxProb(predictions[1]) ? 'text-accent font-bold' : ''}">
                        {(getMaxProb(predictions[0]) * 100).toFixed(0)}%
                      </td>
                      <td class="py-2 text-center text-slate-400">Confidence</td>
                      <td class="py-2 text-right {getMaxProb(predictions[1]) > getMaxProb(predictions[0]) ? 'text-accent font-bold' : ''}">
                        {(getMaxProb(predictions[1]) * 100).toFixed(0)}%
                      </td>
                    </tr>
                    <tr class="border-t border-white/5">
                      <td class="py-2">{predictions[0].prediction?.predicted_scoreline || "?"}</td>
                      <td class="py-2 text-center text-slate-400">Score</td>
                      <td class="py-2 text-right">{predictions[1].prediction?.predicted_scoreline || "?"}</td>
                    </tr>
                    <tr class="border-t border-white/5">
                      <td class="py-2">{((predictions[0].prediction?.btts_prob || 0) * 100).toFixed(0)}%</td>
                      <td class="py-2 text-center text-slate-400">BTTS</td>
                      <td class="py-2 text-right">{((predictions[1].prediction?.btts_prob || 0) * 100).toFixed(0)}%</td>
                    </tr>
                    <tr class="border-t border-white/5">
                      <td class="py-2">{((predictions[0].prediction?.over25_prob || 0) * 100).toFixed(0)}%</td>
                      <td class="py-2 text-center text-slate-400">Over 2.5</td>
                      <td class="py-2 text-right">{((predictions[1].prediction?.over25_prob || 0) * 100).toFixed(0)}%</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          {/if}
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .animate-bounce-in {
    animation: bounceIn 0.3s ease-out;
  }

  @keyframes bounceIn {
    0% {
      transform: scale(0.8);
      opacity: 0;
    }
    50% {
      transform: scale(1.05);
    }
    100% {
      transform: scale(1);
      opacity: 1;
    }
  }
</style>
