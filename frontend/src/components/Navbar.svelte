<script>
  import { Link, useLocation } from "svelte-routing";
  import SearchBar from "./SearchBar.svelte";

  const location = useLocation();
  $: currentPath = $location.pathname;

  let mobileMenuOpen = false;

  function toggleMobileMenu() {
    mobileMenuOpen = !mobileMenuOpen;
    // Prevent body scroll when menu is open
    document.body.style.overflow = mobileMenuOpen ? "hidden" : "";
  }

  function closeMobileMenu() {
    mobileMenuOpen = false;
    document.body.style.overflow = "";
  }

  function isActive(path) {
    if (path === "/") return currentPath === "/";
    return currentPath.startsWith(path);
  }
</script>

<nav
  class="glass sticky top-0 z-50 px-4 md:px-6 py-3 md:py-4 border-b border-white/5 safe-top"
>
  <div class="flex justify-between items-center gap-4">
    <!-- Logo -->
    <Link
      to="/"
      class="flex items-center gap-3 flex-shrink-0 group"
      on:click={closeMobileMenu}
    >
      <div
        class="w-8 h-8 bg-gradient-to-br from-primary to-blue-600 rounded-lg flex items-center justify-center font-bold text-white text-sm shadow-lg shadow-blue-500/20 group-hover:shadow-blue-500/40 transition-all"
      >
        FC
      </div>
      <span
        class="text-lg md:text-xl font-display font-bold tracking-tight text-white group-hover:text-primary transition-colors"
        >FixtureCast</span
      >
    </Link>

    <!-- Desktop Search -->
    <div class="hidden lg:block flex-1 max-w-md mx-8">
      <SearchBar />
    </div>

    <!-- Desktop Navigation -->
    <div class="hidden md:flex gap-1 items-center">
      <Link
        to="/"
        class="px-4 py-2 rounded-lg text-sm font-medium transition-all {isActive(
          '/',
        )
          ? 'text-white bg-white/10'
          : 'text-slate-400 hover:text-white hover:bg-white/5'}"
      >
        Home
      </Link>
      <Link
        to="/fixtures"
        class="px-4 py-2 rounded-lg text-sm font-medium transition-all {isActive(
          '/fixtures',
        )
          ? 'text-white bg-white/10'
          : 'text-slate-400 hover:text-white hover:bg-white/5'}"
      >
        Fixtures
      </Link>
      <Link
        to="/standings"
        class="px-4 py-2 rounded-lg text-sm font-medium transition-all {isActive(
          '/standings',
        )
          ? 'text-white bg-white/10'
          : 'text-slate-400 hover:text-white hover:bg-white/5'}"
      >
        Standings
      </Link>
      <Link
        to="/live"
        class="px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 {isActive(
          '/live',
        )
          ? 'text-white bg-white/10'
          : 'text-slate-400 hover:text-white hover:bg-white/5'}"
      >
        <span class="relative flex h-2 w-2">
          <span
            class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"
          ></span>
          <span class="relative inline-flex rounded-full h-2 w-2 bg-red-500"
          ></span>
        </span>
        Live
      </Link>
      <Link
        to="/predictions"
        class="ml-2 px-4 py-2 rounded-lg text-sm font-bold transition-all flex items-center gap-2 {isActive(
          '/predictions',
        )
          ? 'text-white bg-primary/20 border border-primary/50 shadow-[0_0_10px_rgba(59,130,246,0.3)]'
          : 'text-white bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20'}"
      >
        <svg
          class="w-4 h-4 text-accent"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          ><path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M13 10V3L4 14h7v7l9-11h-7z"
          /></svg
        >
        AI Models
      </Link>
    </div>

    <!-- Mobile: More menu (main nav in bottom bar) -->
    <div class="flex items-center gap-2 md:hidden">
      <!-- More menu for secondary items -->
      <button
        on:click={toggleMobileMenu}
        class="p-2 rounded-lg hover:bg-white/10 touch-target btn-press text-slate-400 hover:text-white"
        aria-label="More options"
        aria-expanded={mobileMenuOpen}
      >
        <svg
          class="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M4 6h16M4 12h16M4 18h16"
          />
        </svg>
      </button>
    </div>
  </div>

  <!-- Mobile Search (always visible on tablet) -->
  <div class="lg:hidden mt-3">
    <SearchBar />
  </div>
</nav>

<!-- Mobile Menu Overlay -->
{#if mobileMenuOpen}
  <button
    class="mobile-overlay visible md:hidden"
    on:click={closeMobileMenu}
    on:keydown={(e) => e.key === "Escape" && closeMobileMenu()}
    aria-label="Close menu"
    tabindex="-1"
  ></button>
{/if}

<!-- Mobile Menu Drawer (Secondary items only - main nav in bottom bar) -->
<div
  class="fixed inset-y-0 right-0 w-72 max-w-[85vw] bg-surface z-50 transform md:hidden mobile-drawer {mobileMenuOpen
    ? 'open'
    : ''} border-l border-white/10 shadow-2xl"
  style="padding-top: calc(env(safe-area-inset-top) + 1rem);"
>
  <div class="flex flex-col h-full">
    <!-- Menu Header -->
    <div
      class="flex items-center justify-between px-6 pb-6 border-b border-white/5"
    >
      <span class="font-display font-bold text-xl">Menu</span>
      <button
        on:click={closeMobileMenu}
        class="p-2 -mr-2 rounded-lg hover:bg-white/10 touch-target btn-press text-slate-400 hover:text-white"
        aria-label="Close menu"
      >
        <svg
          class="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>
    </div>

    <!-- Secondary Navigation Links -->
    <nav class="flex-1 overflow-y-auto py-6">
      <div class="space-y-1 px-3">
        <Link
          to="/teams"
          on:click={closeMobileMenu}
          class="flex items-center gap-4 px-4 py-3 rounded-xl hover:bg-white/5 touch-target menu-item group"
        >
          <div
            class="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 group-hover:bg-emerald-500/20 transition-colors"
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
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              /></svg
            >
          </div>
          <span class="font-medium text-slate-200 group-hover:text-white"
            >Teams</span
          >
        </Link>

        <Link
          to="/results"
          on:click={closeMobileMenu}
          class="flex items-center gap-4 px-4 py-3 rounded-xl hover:bg-white/5 touch-target menu-item group"
        >
          <div
            class="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400 group-hover:bg-blue-500/20 transition-colors"
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
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 002 2h2a2 2 0 002-2z"
              /></svg
            >
          </div>
          <span class="font-medium text-slate-200 group-hover:text-white"
            >Results</span
          >
        </Link>

        <div class="my-4 mx-4 border-t border-white/5"></div>

        <Link
          to="/models"
          on:click={closeMobileMenu}
          class="flex items-center gap-4 px-4 py-3 rounded-xl hover:bg-white/5 touch-target menu-item group"
        >
          <div
            class="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-400 group-hover:bg-purple-500/20 transition-colors"
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
                d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
              /></svg
            >
          </div>
          <span class="font-medium text-slate-200 group-hover:text-white"
            >Model Stats</span
          >
        </Link>

        <Link
          to="/history"
          on:click={closeMobileMenu}
          class="flex items-center gap-4 px-4 py-3 rounded-xl hover:bg-white/5 touch-target menu-item group"
        >
          <div
            class="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-400 group-hover:bg-amber-500/20 transition-colors"
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
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              /></svg
            >
          </div>
          <span class="font-medium text-slate-200 group-hover:text-white"
            >History</span
          >
        </Link>
      </div>
    </nav>

    <!-- Menu Footer -->
    <div class="p-6 border-t border-white/5 safe-bottom bg-black/20">
      <div class="text-xs text-slate-500 text-center font-medium">
        FixtureCast v1.1 • AI-Powered Predictions
      </div>
    </div>
  </div>
</div>
