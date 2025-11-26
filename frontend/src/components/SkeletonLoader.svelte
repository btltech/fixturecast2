<script>
  // Skeleton Loader Component
  // Usage: <SkeletonLoader type="card|text|avatar|bar|fixture" />
  export let type = "text";
  export let width = "100%";
  export let height = "1rem";
  export let count = 1;
  export let className = "";
</script>

{#if type === "text"}
  {#each Array(count) as _, i}
    <div
      class="skeleton-pulse rounded {className}"
      style="width: {width}; height: {height}; margin-bottom: {i < count - 1 ? '0.5rem' : '0'}"
    ></div>
  {/each}

{:else if type === "avatar"}
  <div class="skeleton-pulse rounded-full {className}" style="width: {width}; height: {height}"></div>

{:else if type === "card"}
  <div class="glass-card p-4 {className}">
    <div class="flex items-center gap-3 mb-4">
      <div class="skeleton-pulse w-12 h-12 rounded-full"></div>
      <div class="flex-1">
        <div class="skeleton-pulse h-4 w-3/4 rounded mb-2"></div>
        <div class="skeleton-pulse h-3 w-1/2 rounded"></div>
      </div>
    </div>
    <div class="skeleton-pulse h-3 w-full rounded mb-2"></div>
    <div class="skeleton-pulse h-3 w-5/6 rounded mb-2"></div>
    <div class="skeleton-pulse h-3 w-4/6 rounded"></div>
  </div>

{:else if type === "fixture"}
  <div class="glass-card p-4 {className}">
    <div class="flex items-center justify-between mb-3">
      <div class="skeleton-pulse h-3 w-20 rounded"></div>
      <div class="skeleton-pulse h-4 w-16 rounded"></div>
    </div>
    <div class="flex items-center justify-between mb-4">
      <!-- Home Team -->
      <div class="flex-1 text-center">
        <div class="skeleton-pulse w-12 h-12 rounded-full mx-auto mb-2"></div>
        <div class="skeleton-pulse h-3 w-20 rounded mx-auto"></div>
      </div>
      <!-- VS -->
      <div class="px-3">
        <div class="skeleton-pulse h-6 w-8 rounded"></div>
      </div>
      <!-- Away Team -->
      <div class="flex-1 text-center">
        <div class="skeleton-pulse w-12 h-12 rounded-full mx-auto mb-2"></div>
        <div class="skeleton-pulse h-3 w-20 rounded mx-auto"></div>
      </div>
    </div>
    <div class="skeleton-pulse h-10 w-full rounded-lg"></div>
  </div>

{:else if type === "prediction"}
  <div class="glass-card p-6 {className}">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <!-- Home -->
      <div class="flex-1 text-center">
        <div class="skeleton-pulse w-20 h-20 rounded-full mx-auto mb-3"></div>
        <div class="skeleton-pulse h-5 w-24 rounded mx-auto mb-1"></div>
        <div class="skeleton-pulse h-3 w-12 rounded mx-auto"></div>
      </div>
      <!-- Score -->
      <div class="px-6 text-center">
        <div class="skeleton-pulse h-3 w-20 rounded mx-auto mb-2"></div>
        <div class="skeleton-pulse h-12 w-24 rounded mx-auto mb-2"></div>
        <div class="skeleton-pulse h-4 w-32 rounded mx-auto"></div>
      </div>
      <!-- Away -->
      <div class="flex-1 text-center">
        <div class="skeleton-pulse w-20 h-20 rounded-full mx-auto mb-3"></div>
        <div class="skeleton-pulse h-5 w-24 rounded mx-auto mb-1"></div>
        <div class="skeleton-pulse h-3 w-12 rounded mx-auto"></div>
      </div>
    </div>
    <!-- Probability Bar -->
    <div class="skeleton-pulse h-6 w-full rounded-full"></div>
  </div>

{:else if type === "bar"}
  <div class="skeleton-pulse rounded-full {className}" style="width: {width}; height: {height}"></div>

{:else if type === "stats"}
  <div class="glass-card p-4 {className}">
    <div class="skeleton-pulse h-5 w-32 rounded mb-4"></div>
    <div class="space-y-3">
      {#each Array(4) as _}
        <div>
          <div class="flex justify-between mb-1">
            <div class="skeleton-pulse h-3 w-24 rounded"></div>
            <div class="skeleton-pulse h-3 w-12 rounded"></div>
          </div>
          <div class="skeleton-pulse h-2 w-full rounded-full"></div>
        </div>
      {/each}
    </div>
  </div>

{:else}
  <div class="skeleton-pulse rounded {className}" style="width: {width}; height: {height}"></div>
{/if}

<style>
  .skeleton-pulse {
    background: linear-gradient(
      90deg,
      rgba(255, 255, 255, 0.04) 0%,
      rgba(255, 255, 255, 0.08) 50%,
      rgba(255, 255, 255, 0.04) 100%
    );
    background-size: 200% 100%;
    animation: skeleton-shimmer 1.3s linear infinite;
  }

  @keyframes skeleton-shimmer {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
    }
  }

  /* Respect reduced motion */
  @media (prefers-reduced-motion: reduce) {
    .skeleton-pulse {
      animation: none;
      background: rgba(255, 255, 255, 0.06);
    }
  }
</style>
