<script>
  // Mobile Bottom Navigation Component
  // Fixed bottom nav bar for better mobile UX
  import { Link, useLocation } from "svelte-routing";

  // Get reactive location store
  const location = useLocation();

  // Reactive current path derived from location store
  $: currentPath = $location.pathname;

  const navItems = [
    {
      path: "/",
      label: "Home",
      svgPath:
        "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6",
    },
    {
      path: "/fixtures",
      label: "Fixtures",
      svgPath:
        "M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z",
    },
    {
      path: "/live",
      label: "Live",
      pulse: true,
      svgPath:
        "M5.636 18.364a9 9 0 010-12.728m12.728 0a9 9 0 010 12.728m-9.9-2.829a5 5 0 010-7.07m7.072 0a5 5 0 010 7.07M13 12a1 1 0 11-2 0 1 1 0 012 0z",
    },
    {
      path: "/predictions",
      label: "AI",
      svgPath:
        "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z",
    },
    {
      path: "/standings",
      label: "Table",
      svgPath:
        "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 002 2h2a2 2 0 002-2z",
    },
  ];

  function isActive(path) {
    if (path === "/") return currentPath === "/";
    return currentPath.startsWith(path);
  }
</script>

<!-- Mobile Bottom Navigation - only visible on mobile -->
<nav
  class="fixed bottom-0 inset-x-0 z-50 md:hidden bg-surface/90 backdrop-blur-xl border-t border-white/5 safe-bottom shadow-[0_-4px_20px_rgba(0,0,0,0.2)]"
>
  <div class="flex justify-around items-center h-16">
    {#each navItems as item}
      <Link
        to={item.path}
        class="group flex flex-col items-center justify-center flex-1 h-full py-1 btn-press relative"
      >
        <!-- Active Background Glow -->
        {#if isActive(item.path)}
          <div
            class="absolute inset-0 bg-gradient-to-t from-primary/10 to-transparent opacity-50"
          ></div>
        {/if}

        <span
          class="relative mb-1 transition-transform duration-200 group-active:scale-90 {isActive(
            item.path,
          )
            ? '-translate-y-1'
            : ''}"
        >
          <svg
            class="w-6 h-6 {isActive(item.path)
              ? 'text-primary drop-shadow-[0_0_8px_rgba(59,130,246,0.5)]'
              : 'text-slate-500 group-hover:text-slate-300'}"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width={isActive(item.path) ? 2.5 : 2}
              d={item.svgPath}
            />
          </svg>

          {#if item.pulse && !isActive(item.path)}
            <span class="absolute -top-0.5 -right-0.5 flex h-2.5 w-2.5">
              <span
                class="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"
              ></span>
              <span
                class="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500 border border-surface"
              ></span>
            </span>
          {/if}
        </span>

        <span
          class="text-[10px] font-medium transition-all duration-200 {isActive(
            item.path,
          )
            ? 'text-primary translate-y-0'
            : 'text-slate-500 group-hover:text-slate-300 translate-y-0.5'}"
        >
          {item.label}
        </span>

        {#if isActive(item.path)}
          <span
            class="absolute top-0 w-12 h-0.5 bg-gradient-to-r from-transparent via-primary to-transparent shadow-[0_0_8px_rgba(59,130,246,0.8)]"
          ></span>
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
</style>
