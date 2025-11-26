<script>
  import { Link } from "svelte-routing";
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
    <h1 class="text-3xl font-bold text-white mb-2">Privacy Policy</h1>
    <p class="text-slate-400 mb-8">Last updated: November 2025</p>

    <div class="prose prose-invert max-w-none space-y-6 text-slate-300">
      <section>
        <h2 class="text-xl font-semibold text-white mb-3">1. Introduction</h2>
        <p>
          FixtureCast ("we", "our", "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, and protect your personal data in accordance with the UK General Data Protection Regulation (UK GDPR) and the Data Protection Act 2018.
        </p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">2. Data Controller</h2>
        <p>
          FixtureCast is the data controller responsible for your personal data. For any privacy-related queries, please contact us at privacy@fixturecast.com.
        </p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">3. Data We Collect</h2>
        <p>We may collect the following types of data:</p>
        <ul class="list-disc pl-6 mt-2 space-y-1">
          <li><strong>Technical Data:</strong> IP address, browser type, device information, and operating system</li>
          <li><strong>Usage Data:</strong> Pages visited, features used, and time spent on the site</li>
          <li><strong>Cookie Data:</strong> Information stored via cookies (see our Cookie Policy)</li>
        </ul>
        <p class="mt-3">
          We do <strong>not</strong> collect: names, email addresses, payment information, or gambling activity data.
        </p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">4. How We Use Your Data</h2>
        <p>We use your data to:</p>
        <ul class="list-disc pl-6 mt-2 space-y-1">
          <li>Provide and improve our prediction services</li>
          <li>Analyse site usage to enhance user experience</li>
          <li>Ensure site security and prevent fraud</li>
          <li>Comply with legal obligations</li>
        </ul>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">5. Legal Basis for Processing</h2>
        <p>We process your data based on:</p>
        <ul class="list-disc pl-6 mt-2 space-y-1">
          <li><strong>Consent:</strong> For analytics cookies (which you can withdraw at any time)</li>
          <li><strong>Legitimate Interests:</strong> For site functionality, security, and improvement</li>
          <li><strong>Legal Obligation:</strong> Where required by UK law</li>
        </ul>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">6. Data Sharing</h2>
        <p>
          We do not sell your personal data. We may share data with:
        </p>
        <ul class="list-disc pl-6 mt-2 space-y-1">
          <li>Hosting providers (for site operation)</li>
          <li>Analytics services (if you consent to analytics cookies)</li>
          <li>Law enforcement (if legally required)</li>
        </ul>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">7. Data Retention</h2>
        <p>
          We retain technical and usage data for up to 12 months, after which it is anonymised or deleted. Cookie consent preferences are stored locally on your device.
        </p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">8. Your Rights</h2>
        <p>Under UK GDPR, you have the right to:</p>
        <ul class="list-disc pl-6 mt-2 space-y-1">
          <li><strong>Access:</strong> Request a copy of your data</li>
          <li><strong>Rectification:</strong> Correct inaccurate data</li>
          <li><strong>Erasure:</strong> Request deletion of your data</li>
          <li><strong>Portability:</strong> Receive your data in a portable format</li>
          <li><strong>Object:</strong> Object to processing based on legitimate interests</li>
          <li><strong>Withdraw Consent:</strong> Withdraw cookie consent at any time</li>
        </ul>
        <p class="mt-3">
          To exercise these rights, contact privacy@fixturecast.com.
        </p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">9. International Transfers</h2>
        <p>
          Your data may be processed on servers located outside the UK. Where this occurs, we ensure appropriate safeguards are in place (e.g., Standard Contractual Clauses).
        </p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">10. Complaints</h2>
        <p>
          If you have concerns about how we handle your data, you can contact the Information Commissioner's Office (ICO) at <a href="https://ico.org.uk" target="_blank" rel="noopener noreferrer" class="text-cyan-400 hover:underline">ico.org.uk</a> or call 0303 123 1113.
        </p>
      </section>

      <section>
        <h2 class="text-xl font-semibold text-white mb-3">11. Changes to This Policy</h2>
        <p>
          We may update this policy from time to time. Changes will be posted on this page with an updated "Last updated" date.
        </p>
      </section>
    </div>
  </div>
</div>
