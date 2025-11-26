<script>
  import { Link } from "svelte-routing";

  function resetCookieConsent() {
    localStorage.removeItem('fixturecast_cookie_consent');
    window.location.reload();
  }
</script>

<div class="page-enter max-w-4xl mx-auto">
  <div class="element-enter stagger-1">
    <Link to="/" class="inline-flex items-center text-cyan-400 hover:text-cyan-300 mb-6">
      <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
      </svg>
      Back to Home
    </Link>
  </div>

  <div class="glass-card p-8 element-enter stagger-2">
    <h1 class="text-3xl font-bold text-white mb-2">Cookie Policy</h1>
    <p class="text-slate-400 mb-8">Last updated: November 2025</p>

    <div class="prose prose-invert max-w-none space-y-6 text-slate-300">
      <section>
        <h2 class="text-xl font-semibold text-white mb-3">1. What Are Cookies?</h2>
        <p>
          Cookies are small text files stored on your device when you visit a website. They help websites remember your preferences and understand how you use the site.
        </p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">2. Cookies We Use</h2>

        <h3 class="text-lg font-medium text-white mt-4 mb-2">Essential Cookies</h3>
        <p>These are necessary for the website to function and cannot be disabled.</p>
        <div class="overflow-x-auto mt-3">
          <table class="w-full text-sm">
            <thead class="bg-slate-700">
              <tr>
                <th class="px-4 py-2 text-left text-white">Cookie</th>
                <th class="px-4 py-2 text-left text-white">Purpose</th>
                <th class="px-4 py-2 text-left text-white">Duration</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-700">
              <tr>
                <td class="px-4 py-2">fixturecast_cookie_consent</td>
                <td class="px-4 py-2">Stores your cookie preferences</td>
                <td class="px-4 py-2">1 year</td>
              </tr>
              <tr>
                <td class="px-4 py-2">fixturecast_compare</td>
                <td class="px-4 py-2">Stores fixtures selected for comparison</td>
                <td class="px-4 py-2">Session</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h3 class="text-lg font-medium text-white mt-6 mb-2">Analytics Cookies (Optional)</h3>
        <p>These help us understand how visitors use our site. They are only set if you consent.</p>
        <div class="overflow-x-auto mt-3">
          <table class="w-full text-sm">
            <thead class="bg-slate-700">
              <tr>
                <th class="px-4 py-2 text-left text-white">Cookie</th>
                <th class="px-4 py-2 text-left text-white">Purpose</th>
                <th class="px-4 py-2 text-left text-white">Duration</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-700">
              <tr>
                <td class="px-4 py-2">_ga</td>
                <td class="px-4 py-2">Google Analytics - distinguishes users</td>
                <td class="px-4 py-2">2 years</td>
              </tr>
              <tr>
                <td class="px-4 py-2">_gid</td>
                <td class="px-4 py-2">Google Analytics - distinguishes users</td>
                <td class="px-4 py-2">24 hours</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">3. Managing Cookies</h2>
        <p>You can manage your cookie preferences in several ways:</p>
        <ul class="list-disc pl-6 mt-2 space-y-1">
          <li><strong>Our Cookie Banner:</strong> Use the cookie banner when you first visit to accept or reject optional cookies</li>
          <li><strong>Reset Preferences:</strong> Click the button below to reset your cookie choices</li>
          <li><strong>Browser Settings:</strong> Most browsers allow you to block or delete cookies in settings</li>
        </ul>

        <div class="mt-4">
          <button
            on:click={resetCookieConsent}
            class="px-4 py-2 bg-cyan-600 text-white rounded-lg hover:bg-cyan-700 transition-colors btn-interact"
          >
            Reset Cookie Preferences
          </button>
        </div>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">4. Third-Party Cookies</h2>
        <p>
          Some cookies may be set by third-party services we use, such as:
        </p>
        <ul class="list-disc pl-6 mt-2 space-y-1">
          <li><strong>Google Analytics:</strong> For understanding site usage (if you consent)</li>
          <li><strong>API-Football:</strong> For loading team logos and images</li>
        </ul>
        <p class="mt-3">
          These third parties have their own privacy policies governing how they use cookies.
        </p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">5. Browser Cookie Settings</h2>
        <p>You can also manage cookies through your browser:</p>
        <ul class="list-disc pl-6 mt-2 space-y-1">
          <li><a href="https://support.google.com/chrome/answer/95647" target="_blank" rel="noopener noreferrer" class="text-cyan-400 hover:underline">Chrome</a></li>
          <li><a href="https://support.mozilla.org/en-US/kb/cookies-information-websites-store-on-your-computer" target="_blank" rel="noopener noreferrer" class="text-cyan-400 hover:underline">Firefox</a></li>
          <li><a href="https://support.apple.com/en-gb/guide/safari/sfri11471/mac" target="_blank" rel="noopener noreferrer" class="text-cyan-400 hover:underline">Safari</a></li>
          <li><a href="https://support.microsoft.com/en-us/microsoft-edge/delete-cookies-in-microsoft-edge-63947406-40ac-c3b8-57b9-2a946a29ae09" target="_blank" rel="noopener noreferrer" class="text-cyan-400 hover:underline">Edge</a></li>
        </ul>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">6. Changes to This Policy</h2>
        <p>
          We may update this Cookie Policy from time to time. Changes will be posted on this page with an updated "Last updated" date.
        </p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">7. Contact</h2>
        <p>
          For questions about our use of cookies, please contact privacy@fixturecast.com.
        </p>
      </section>
    </div>
  </div>
</div>
