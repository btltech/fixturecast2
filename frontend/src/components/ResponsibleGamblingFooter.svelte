<script>
  import { Link } from "svelte-routing";
</script>

<footer class="bg-slate-900/80 border-t border-slate-700 mt-8">
  <!-- Responsible Gambling Banner -->
  <div class="bg-gradient-to-r from-amber-900/30 to-orange-900/30 border-b border-amber-700/30">
    <div class="container mx-auto px-4 py-3">
      <div class="flex flex-wrap items-center justify-center gap-4 text-sm">
        <span class="text-amber-400 font-medium">🔞 18+ Only</span>
        <span class="text-slate-400">|</span>
        <span class="text-slate-300">If gambling is affecting you, call the National Gambling Helpline:</span>
        <a href="tel:08088020133" class="text-cyan-400 hover:text-cyan-300 font-medium">0808 8020 133</a>
        <span class="text-slate-400 hidden md:inline">|</span>
        <div class="flex gap-3">
          <a href="https://www.gamcare.org.uk" target="_blank" rel="noopener noreferrer" class="text-cyan-400 hover:text-cyan-300">
            GamCare
          </a>
          <a href="https://www.begambleaware.org" target="_blank" rel="noopener noreferrer" class="text-cyan-400 hover:text-cyan-300">
            BeGambleAware
          </a>
        </div>
      </div>
    </div>
  </div>

  <!-- Main Footer -->
  <div class="container mx-auto px-4 py-6">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
      <!-- Brand -->
      <div>
        <h3 class="text-lg font-bold text-white mb-2">⚽ FixtureCast</h3>
        <p class="text-sm text-slate-400">
          AI-powered football match predictions using an 8-model ML ensemble.
        </p>
      </div>

      <!-- Quick Links -->
      <div>
        <h4 class="font-medium text-white mb-3">Quick Links</h4>
        <ul class="space-y-2 text-sm">
          <li><Link to="/" class="text-slate-400 hover:text-cyan-400">Home</Link></li>
          <li><Link to="/fixtures" class="text-slate-400 hover:text-cyan-400">Fixtures</Link></li>
          <li><Link to="/predictions" class="text-slate-400 hover:text-cyan-400">ML Predictions</Link></li>
          <li><Link to="/standings" class="text-slate-400 hover:text-cyan-400">Standings</Link></li>
        </ul>
      </div>

      <!-- Legal -->
      <div>
        <h4 class="font-medium text-white mb-3">Legal</h4>
        <ul class="space-y-2 text-sm">
          <li><Link to="/privacy" class="text-slate-400 hover:text-cyan-400">Privacy Policy</Link></li>
          <li><Link to="/terms" class="text-slate-400 hover:text-cyan-400">Terms of Service</Link></li>
          <li><Link to="/cookies" class="text-slate-400 hover:text-cyan-400">Cookie Policy</Link></li>
        </ul>
      </div>

      <!-- Support -->
      <div>
        <h4 class="font-medium text-white mb-3">Gambling Support</h4>
        <ul class="space-y-2 text-sm">
          <li>
            <a href="https://www.gamcare.org.uk" target="_blank" rel="noopener noreferrer" class="text-slate-400 hover:text-cyan-400">
              GamCare
            </a>
          </li>
          <li>
            <a href="https://www.begambleaware.org" target="_blank" rel="noopener noreferrer" class="text-slate-400 hover:text-cyan-400">
              BeGambleAware
            </a>
          </li>
          <li>
            <a href="https://www.gamblingtherapy.org" target="_blank" rel="noopener noreferrer" class="text-slate-400 hover:text-cyan-400">
              Gambling Therapy
            </a>
          </li>
        </ul>
      </div>
    </div>

    <!-- Disclaimer -->
    <div class="border-t border-slate-700 pt-4">
      <p class="text-xs text-slate-500 text-center mb-4">
        <strong>Disclaimer:</strong> FixtureCast provides match predictions for entertainment and informational purposes only.
        These predictions do not constitute betting advice and should not be relied upon for gambling decisions.
        Past performance does not guarantee future results. Always gamble responsibly.
      </p>

      <div class="flex flex-wrap justify-center items-center gap-4 text-xs text-slate-500">
        <span>&copy; 2025 FixtureCast ML</span>
        <span>|</span>
        <span>Data by API-Football</span>
        <span>|</span>
        <span>Built in the UK 🇬🇧</span>
      </div>
    </div>
  </div>
</footer>
