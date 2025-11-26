<script>
  import { Link } from "svelte-routing";
  import SearchBar from "./SearchBar.svelte";

  let mobileMenuOpen = false;

  function toggleMobileMenu() {
    mobileMenuOpen = !mobileMenuOpen;
    // Prevent body scroll when menu is open
    document.body.style.overflow = mobileMenuOpen ? 'hidden' : '';
  }

  function closeMobileMenu() {
    mobileMenuOpen = false;
    document.body.style.overflow = '';
  }
</script>

<nav class="glass sticky top-0 z-50 px-4 md:px-6 py-3 md:py-4 border-b border-white/10 safe-top">
  <div class="flex justify-between items-center gap-4">
    <!-- Logo -->
    <Link to="/" class="flex items-center gap-2 flex-shrink-0" on:click={closeMobileMenu}>
      <div
        class="w-8 h-8 bg-gradient-to-br from-accent to-blue-600 rounded-lg flex items-center justify-center font-bold text-white text-sm"
      >
        FC
      </div>
      <span class="text-lg md:text-xl font-bold tracking-tight">FixtureCast</span>
    </Link>

    <!-- Desktop Search -->
    <div class="hidden lg:block flex-1 max-w-md mx-8">
      <SearchBar />
    </div>

    <!-- Desktop Navigation -->
    <div class="hidden md:flex gap-3 lg:gap-4 text-sm font-medium text-slate-300 items-center">
      <Link to="/" class="hover:text-white py-2 nav-link">Home</Link>
      <Link to="/fixtures" class="hover:text-white py-2 nav-link">Fixtures</Link>
      <Link to="/standings" class="hover:text-white py-2 nav-link">Standings</Link>
      <Link to="/live" class="hover:text-white flex items-center gap-1 py-2 nav-link">
        <span class="relative flex h-2 w-2">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
        </span>
        <span>Live</span>
      </Link>
      <Link to="/predictions" class="hover:text-white flex items-center gap-1 py-2 nav-link">
        <span>🧠</span>
        <span>AI</span>
      </Link>
    </div>

    <!-- Mobile: More menu (main nav in bottom bar) -->
    <div class="flex items-center gap-2 md:hidden">
      <!-- More menu for secondary items -->
      <button
        on:click={toggleMobileMenu}
        class="p-2 rounded-lg hover:bg-white/10 touch-target btn-press"
        aria-label="More options"
        aria-expanded={mobileMenuOpen}
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
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
    on:keydown={(e) => e.key === 'Escape' && closeMobileMenu()}
    aria-label="Close menu"
    tabindex="-1"
  ></button>
{/if}

<!-- Mobile Menu Drawer (Secondary items only - main nav in bottom bar) -->
<div 
  class="fixed inset-y-0 right-0 w-72 max-w-[85vw] bg-slate-900 z-50 transform md:hidden mobile-drawer {mobileMenuOpen ? 'open' : ''}"
  style="padding-top: calc(env(safe-area-inset-top) + 1rem);"
>
  <div class="flex flex-col h-full">
    <!-- Menu Header -->
    <div class="flex items-center justify-between px-4 pb-4 border-b border-white/10">
      <span class="font-bold text-lg">More Options</span>
      <button
        on:click={closeMobileMenu}
        class="p-2 rounded-lg hover:bg-white/10 touch-target btn-press"
        aria-label="Close menu"
      >
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Secondary Navigation Links -->
    <nav class="flex-1 overflow-y-auto py-4">
      <div class="space-y-1 px-2">
        <Link 
          to="/teams" 
          on:click={closeMobileMenu}
          class="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-white/10 touch-target menu-item"
        >
          <span class="text-xl">🛡️</span>
          <span class="font-medium">Teams</span>
        </Link>
        
        <Link 
          to="/results" 
          on:click={closeMobileMenu}
          class="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-white/10 touch-target menu-item"
        >
          <span class="text-xl">📊</span>
          <span class="font-medium">Results</span>
        </Link>
        
        <div class="my-3 mx-4 border-t border-white/10"></div>
        
        <Link 
          to="/models" 
          on:click={closeMobileMenu}
          class="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-white/10 touch-target menu-item"
        >
          <span class="text-xl">📈</span>
          <span class="font-medium">Model Stats</span>
        </Link>
        
        <Link 
          to="/history" 
          on:click={closeMobileMenu}
          class="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-white/10 touch-target menu-item"
        >
          <span class="text-xl">📚</span>
          <span class="font-medium">History</span>
        </Link>

        <div class="my-3 mx-4 border-t border-white/10"></div>
        
        <div class="px-4 py-3">
          <div class="text-xs text-slate-400 mb-2">Quick Navigation</div>
          <p class="text-xs text-slate-500">
            Use the bottom navigation bar for main sections: Home, Fixtures, Live, AI Predictions, and Standings.
          </p>
        </div>
      </div>
    </nav>

    <!-- Menu Footer -->
    <div class="p-4 border-t border-white/10 safe-bottom">
      <div class="text-xs text-slate-500 text-center">
        FixtureCast v1.1 • AI-Powered Predictions
      </div>
    </div>
  </div>
</div>
