<script>
  // Mobile Bottom Navigation Component
  // Fixed bottom nav bar for better mobile UX
  import { Link } from "svelte-routing";

  export let currentPath = "/";

  const navItems = [
    { path: "/", icon: "🏠", label: "Home", activeIcon: "🏠" },
    { path: "/fixtures", icon: "📅", label: "Fixtures", activeIcon: "📅" },
    { path: "/live", icon: "🔴", label: "Live", activeIcon: "🔴", pulse: true },
    { path: "/predictions", icon: "🧠", label: "AI", activeIcon: "🧠" },
    { path: "/standings", icon: "🏆", label: "Table", activeIcon: "🏆" },
  ];

  function isActive(path) {
    if (path === "/") return currentPath === "/";
    return currentPath.startsWith(path);
  }
</script>

<!-- Mobile Bottom Navigation - only visible on mobile -->
<nav class="fixed bottom-0 inset-x-0 z-50 md:hidden bg-slate-900/95 backdrop-blur-lg border-t border-white/10 safe-bottom">
  <div class="flex justify-around items-center h-16">
    {#each navItems as item}
      <Link
        to={item.path}
        class="flex flex-col items-center justify-center flex-1 h-full py-1 btn-press {isActive(item.path) ? 'text-accent' : 'text-slate-400'}"
      >
        <span class="relative text-xl mb-0.5 icon-hover">
          {item.icon}
          {#if item.pulse && !isActive(item.path)}
            <span class="absolute -top-0.5 -right-0.5 flex h-2 w-2">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
            </span>
          {/if}
        </span>
        <span class="text-[10px] font-medium transition-colors {isActive(item.path) ? 'text-accent' : 'text-slate-500'}">
          {item.label}
        </span>
        {#if isActive(item.path)}
          <span class="absolute bottom-0 w-12 h-0.5 bg-accent rounded-t-full nav-indicator"></span>
        {/if}
      </Link>
    {/each}
  </div>
</nav>

<!-- Spacer to prevent content being hidden behind bottom nav on mobile -->
<div class="h-16 md:hidden"></div>

<style>
  .safe-bottom {
    padding-bottom: env(safe-area-inset-bottom);
  }

  /* Smooth indicator transitions handled by global nav-indicator class */
</style>
