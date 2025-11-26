<script>
  import { Router, Link, Route } from "svelte-routing";
  import { onMount } from "svelte";
  import Navbar from "./components/Navbar.svelte";
  import BottomNav from "./components/BottomNav.svelte";
  import ComparePanel from "./components/ComparePanel.svelte";
  import CookieConsent from "./components/CookieConsent.svelte";
  import ResponsibleGamblingFooter from "./components/ResponsibleGamblingFooter.svelte";
  import Home from "./pages/Home.svelte";
  import Fixtures from "./pages/Fixtures.svelte";
  import Prediction from "./pages/Prediction.svelte";
  import Teams from "./pages/Teams.svelte";
  import TeamDetail from "./pages/TeamDetail.svelte";
  import MLPredictions from "./pages/MLPredictions.svelte";
  import Standings from "./pages/Standings.svelte";
  import Results from "./pages/Results.svelte";
  import ModelStats from "./pages/ModelStats.svelte";
  import History from "./pages/History.svelte";
  import LiveScores from "./pages/LiveScores.svelte";
  import Privacy from "./pages/Privacy.svelte";
  import Terms from "./pages/Terms.svelte";
  import Cookies from "./pages/Cookies.svelte";

  export let url = "";

  // Track current path for bottom nav - reactive to URL changes
  let currentPath = typeof window !== "undefined" ? window.location.pathname : "/";

  // Update path on navigation (browser back/forward)
  function handleNavigation() {
    currentPath = window.location.pathname;
  }

  // Use MutationObserver pattern to detect URL changes from Link clicks
  onMount(() => {
    // Set initial path
    currentPath = window.location.pathname;

    // Listen for clicks that might change the URL (Link components use history.pushState)
    const handleClick = () => {
      // Small delay to allow pushState to complete
      setTimeout(() => {
        if (currentPath !== window.location.pathname) {
          currentPath = window.location.pathname;
        }
      }, 0);
    };

    document.addEventListener("click", handleClick);

    return () => {
      document.removeEventListener("click", handleClick);
    };
  });
</script>

<svelte:window on:popstate={handleNavigation} />

<Router {url}>
  <div class="min-h-screen flex flex-col pb-16 md:pb-0">
    <Navbar />
    <main class="flex-grow container mx-auto p-4">
      <Route path="/" component={Home} />
      <Route path="/fixtures" component={Fixtures} />
      <Route path="/prediction/:id" component={Prediction} />
      <Route path="/predictions" component={MLPredictions} />
      <Route path="/teams" component={Teams} />
      <Route path="/team/:id" component={TeamDetail} />
      <Route path="/standings" component={Standings} />
      <Route path="/results" component={Results} />
      <Route path="/models" component={ModelStats} />
      <Route path="/history" component={History} />
      <Route path="/live" component={LiveScores} />
      <Route path="/privacy" component={Privacy} />
      <Route path="/terms" component={Terms} />
      <Route path="/cookies" component={Cookies} />
    </main>

    <!-- Responsible Gambling Footer -->
    <ResponsibleGamblingFooter />

    <!-- Mobile Bottom Navigation -->
    <BottomNav {currentPath} />

    <!-- Compare Panel (floating) -->
    <ComparePanel />

    <!-- Cookie Consent Banner -->
    <CookieConsent />
  </div>
</Router>
