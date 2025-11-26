<script>
    import { Link } from "svelte-routing";
    import { slide } from "svelte/transition";

    export let prediction;
    export let homeTeam;
    export let awayTeam;
    export let homeTeamId = null;
    export let awayTeamId = null;
    export let leagueId = 39;

    $: homeWinPct = (prediction.home_win_prob * 100).toFixed(1);
    $: drawPct = (prediction.draw_prob * 100).toFixed(1);
    $: awayWinPct = (prediction.away_win_prob * 100).toFixed(1);
    $: bttsPct = (prediction.btts_prob * 100).toFixed(1);
    $: over25Pct = (prediction.over25_prob * 100).toFixed(1);

    // Confidence / intervals (if backend provides them)
    $: confidence = prediction.confidence_intervals
        ? prediction.confidence_intervals
        : null;

    $: confidenceLevel = confidence ? confidence.confidence_level : null;

    function getConfidenceLabel() {
        if (!confidenceLevel) return "Confidence: pending";
        if (confidenceLevel === "very_high") return "Very High Confidence";
        if (confidenceLevel === "high") return "High Confidence";
        if (confidenceLevel === "medium") return "Medium Confidence";
        if (confidenceLevel === "low") return "Low Confidence";
        return "Confidence: analysing";
    }

    function getConfidenceClass() {
        if (!confidenceLevel) return "pending";
        return confidenceLevel;
    }

    let showBreakdown = false;

    function getOutcomeClass(prob) {
        if (prob > 0.5) return "high";
        if (prob > 0.3) return "medium";
        return "low";
    }

    function toggleBreakdown() {
        showBreakdown = !showBreakdown;
    }

    // Simple human-readable reasons using available features if present
    $: reasons = [];

    $: if (prediction && prediction.elo_ratings) {
        const diff = Math.abs(prediction.elo_ratings.diff || 0);
        if (diff >= 80) {
            const favored = prediction.elo_ratings.diff > 0 ? homeTeam : awayTeam;
            reasons = [
                ...reasons,
                `${favored} has a clear Elo rating advantage (~${diff.toFixed(0)} pts)`,
            ];
        }
    }

    $: if (prediction) {
        const homeForm = prediction.home_form_last5 ?? prediction.home_points_last10;
        const awayForm = prediction.away_form_last5 ?? prediction.away_points_last10;
        if (typeof homeForm === "number" && typeof awayForm === "number") {
            const diff = homeForm - awayForm;
            if (diff >= 3) {
                reasons = [
                    ...reasons,
                    `${homeTeam} is in better recent form over the last matches`,
                ];
            } else if (diff <= -3) {
                reasons = [
                    ...reasons,
                    `${awayTeam} is in better recent form over the last matches`,
                ];
            }
        }
    }

    $: if (prediction && typeof prediction.rank_difference === "number") {
        const diff = prediction.rank_difference;
        if (diff < -5) {
            reasons = [
                ...reasons,
                `${homeTeam} sits significantly higher in the table`,
            ];
        } else if (diff > 5) {
            reasons = [
                ...reasons,
                `${awayTeam} sits significantly higher in the table`,
            ];
        }
    }
</script>

<div class="ml-prediction-card">
    <div class="prediction-header">
        <div class="header-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path
                    d="M12 2L2 7L12 12L22 7L12 2Z"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linejoin="round"
                />
                <path
                    d="M2 17L12 22L22 17"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linejoin="round"
                />
                <path
                    d="M2 12L12 17L22 12"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linejoin="round"
                />
            </svg>
        </div>
        <div class="header-title-block">
            <h3>AI-Powered Prediction</h3>
            <div class="confidence-chip {getConfidenceClass()}">
                <span class="dot"></span>
                <span>{getConfidenceLabel()}</span>
            </div>
        </div>
        <button
            class="info-btn"
            on:click={toggleBreakdown}
            title="Model Breakdown"
        >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                <circle
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    stroke-width="2"
                />
                <path
                    d="M12 16V12M12 8H12.01"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                />
            </svg>
        </button>
    </div>

    <!-- Main Prediction -->
    <div class="prediction-main">
        <div class="outcome-bars">
            <div
                class="outcome-bar home {getOutcomeClass(
                    prediction.home_win_prob,
                )}"
            >
                <div class="bar-label">
                    {#if homeTeamId}
                        <Link to="/team/{homeTeamId}?league={leagueId}" class="team-name team-link">{homeTeam}</Link>
                    {:else}
                        <span class="team-name">{homeTeam}</span>
                    {/if}
                    <span class="probability">{homeWinPct}%</span>
                </div>
                <div class="bar-fill" style="width: {homeWinPct}%"></div>
            </div>

            <div
                class="outcome-bar draw {getOutcomeClass(prediction.draw_prob)}"
            >
                <div class="bar-label">
                    <span class="team-name">Draw</span>
                    <span class="probability">{drawPct}%</span>
                </div>
                <div class="bar-fill" style="width: {drawPct}%"></div>
            </div>

            <div
                class="outcome-bar away {getOutcomeClass(
                    prediction.away_win_prob,
                )}"
            >
                <div class="bar-label">
                    {#if awayTeamId}
                        <Link to="/team/{awayTeamId}?league={leagueId}" class="team-name team-link">{awayTeam}</Link>
                    {:else}
                        <span class="team-name">{awayTeam}</span>
                    {/if}
                    <span class="probability">{awayWinPct}%</span>
                </div>
                <div class="bar-fill" style="width: {awayWinPct}%"></div>
            </div>
        </div>

        <!-- Predicted Scoreline -->
        <div class="scoreline-prediction">
            <div class="scoreline-label">Most Likely Score</div>
            <div class="scoreline-value">{prediction.predicted_scoreline}</div>
        </div>

        <!-- Additional Predictions -->
        <div class="additional-predictions">
            <div class="prediction-pill">
                <span class="pill-label">Both Teams to Score</span>
                <span class="pill-value">{bttsPct}%</span>
            </div>
            <div class="prediction-pill">
                <span class="pill-label">Over 2.5 Goals</span>
                <span class="pill-value">{over25Pct}%</span>
            </div>
        </div>

        {#if reasons.length > 0}
            <div class="reasons-block">
                <div class="reasons-title">Why the model leans this way</div>
                <ul>
                    {#each reasons.slice(0, 3) as r}
                        <li>{r}</li>
                    {/each}
                </ul>
            </div>
        {/if}
    </div>

    <!-- Model Breakdown (Expandable) -->
    {#if showBreakdown}
        <div class="model-breakdown" transition:slide>
            <h4>Model Contributions</h4>
            <div class="breakdown-grid">
                {#each Object.entries(prediction.model_breakdown || {}) as [model, probs]}
                    {#if typeof probs === "object" && probs.home_win}
                        <div class="model-card">
                            <div class="model-name">{model.toUpperCase()}</div>
                            <div class="model-probs">
                                <div class="prob-mini">
                                    <span>H</span>
                                    <span
                                        >{(probs.home_win * 100).toFixed(
                                            0,
                                        )}%</span
                                    >
                                </div>
                                <div class="prob-mini">
                                    <span>D</span>
                                    <span>{(probs.draw * 100).toFixed(0)}%</span
                                    >
                                </div>
                                <div class="prob-mini">
                                    <span>A</span>
                                    <span
                                        >{(probs.away_win * 100).toFixed(
                                            0,
                                        )}%</span
                                    >
                                </div>
                            </div>
                        </div>
                    {/if}
                {/each}
            </div>
            <div class="breakdown-note">
                Predictions are ensemble-weighted by historical accuracy
            </div>
        </div>
    {/if}
</div>

<style>
    .ml-prediction-card {
        background: linear-gradient(
            135deg,
            rgba(88, 28, 135, 0.1),
            rgba(139, 92, 246, 0.05)
        );
        border: 1px solid rgba(139, 92, 246, 0.2);
        border-radius: 16px;
        padding: 20px;
        backdrop-filter: blur(20px);
        box-shadow: 0 8px 32px rgba(139, 92, 246, 0.1);
        transition: transform var(--duration-fast, 100ms) var(--ease-out-soft, cubic-bezier(0.25, 0.46, 0.45, 0.94)),
                    box-shadow var(--duration-fast, 100ms) var(--ease-out-soft, cubic-bezier(0.25, 0.46, 0.45, 0.94));
    }

    @media (min-width: 640px) {
        .ml-prediction-card {
            padding: 24px;
        }
    }

    .ml-prediction-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 48px rgba(139, 92, 246, 0.15);
    }

    .prediction-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 24px;
        padding-bottom: 16px;
        border-bottom: 1px solid rgba(139, 92, 246, 0.2);
    }

    .header-icon {
        color: var(--primary-400, #a78bfa);
    }

    .header-title-block {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 4px;
    }

    .prediction-header h3 {
        margin: 0;
        font-size: 1.25rem;
        font-weight: 700;
        background: linear-gradient(135deg, #a78bfa, #ec4899);
        background-clip: text;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .confidence-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 0.7rem;
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(148, 163, 184, 0.4);
        color: #e5e7eb;
        align-self: flex-start;
    }

    .confidence-chip .dot {
        width: 6px;
        height: 6px;
        border-radius: 999px;
        background: #9ca3af;
    }

    .confidence-chip.very_high {
        border-color: #22c55e;
        background: rgba(34, 197, 94, 0.08);
    }

    .confidence-chip.very_high .dot {
        background: #22c55e;
    }

    .confidence-chip.high {
        border-color: #a3e635;
        background: rgba(163, 230, 53, 0.08);
    }

    .confidence-chip.high .dot {
        background: #a3e635;
    }

    .confidence-chip.medium {
        border-color: #fbbf24;
        background: rgba(251, 191, 36, 0.08);
    }

    .confidence-chip.medium .dot {
        background: #fbbf24;
    }

    .confidence-chip.low {
        border-color: #f97316;
        background: rgba(249, 115, 22, 0.08);
    }

    .confidence-chip.low .dot {
        background: #f97316;
    }

    .info-btn {
        background: rgba(139, 92, 246, 0.1);
        border: 1px solid rgba(139, 92, 246, 0.3);
        border-radius: 8px;
        padding: 6px;
        cursor: pointer;
        color: var(--primary-400, #a78bfa);
        transition: background-color var(--duration-fast, 100ms) var(--ease-out-soft, cubic-bezier(0.25, 0.46, 0.45, 0.94)),
                    transform var(--duration-instant, 70ms) var(--ease-out-soft, cubic-bezier(0.25, 0.46, 0.45, 0.94));
    }

    .info-btn:hover {
        background: rgba(139, 92, 246, 0.2);
        transform: scale(1.05);
    }

    .info-btn:active {
        transform: scale(0.97);
    }

    .prediction-main {
        display: flex;
        flex-direction: column;
        gap: 20px;
    }

    @media (min-width: 640px) {
        .prediction-main {
            gap: 24px;
        }
    }

    .outcome-bars {
        display: flex;
        flex-direction: column;
        gap: 12px;
        min-height: 180px; /* Reserve space to prevent layout shift */
    }

    .outcome-bar {
        position: relative;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 12px;
        overflow: hidden;
        min-height: 52px; /* Fixed height for each bar */
    }

    .bar-label {
        display: flex;
        justify-content: space-between;
        align-items: center;
        position: relative;
        z-index: 2;
        margin-bottom: 8px;
    }

    .team-name {
        font-weight: 600;
        font-size: 0.95rem;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        max-width: 180px; /* Limit width to prevent bar overflow */
    }

    .team-link {
        color: inherit;
        text-decoration: none;
        transition: color var(--duration-fast, 100ms) var(--ease-out-soft, cubic-bezier(0.25, 0.46, 0.45, 0.94));
    }

    .team-link:hover {
        color: var(--primary-400, #a78bfa);
        text-decoration: underline;
    }

    .probability {
        font-weight: 700;
        font-size: 1.1rem;
    }

    .bar-fill {
        position: absolute;
        top: 0;
        left: 0;
        height: 100%;
        border-radius: 12px;
        transition: width var(--duration-slow, 300ms) var(--ease-out-smooth, cubic-bezier(0.22, 1, 0.36, 1)) 50ms; /* Slight delay to ensure layout is ready */
        opacity: 0.3;
        width: 0; /* Start at 0, animate to target */
    }

    .outcome-bar.home .bar-fill {
        background: linear-gradient(90deg, #10b981, #059669);
    }

    .outcome-bar.draw .bar-fill {
        background: linear-gradient(90deg, #f59e0b, #d97706);
    }

    .outcome-bar.away .bar-fill {
        background: linear-gradient(90deg, #ef4444, #dc2626);
    }

    .outcome-bar.high .bar-fill {
        opacity: 0.6;
        box-shadow: 0 0 20px currentColor;
    }

    .outcome-bar.medium .bar-fill {
        opacity: 0.4;
    }

    .scoreline-prediction {
        text-align: center;
        padding: 20px;
        background: rgba(139, 92, 246, 0.1);
        border-radius: 12px;
        border: 1px dashed rgba(139, 92, 246, 0.3);
    }

    .scoreline-label {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        opacity: 0.7;
        margin-bottom: 8px;
    }

    .scoreline-value {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #a78bfa, #ec4899);
        background-clip: text;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: "Courier New", monospace;
    }

    .additional-predictions {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
    }

    .prediction-pill {
        background: rgba(59, 130, 246, 0.1);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 10px;
        padding: 12px 16px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 6px;
        transition: transform var(--duration-fast, 100ms) var(--ease-out-soft, cubic-bezier(0.25, 0.46, 0.45, 0.94)),
                    background-color var(--duration-fast, 100ms) var(--ease-out-soft, cubic-bezier(0.25, 0.46, 0.45, 0.94));
    }

    .prediction-pill:hover {
        transform: scale(1.02);
        background: rgba(59, 130, 246, 0.15);
    }

    .pill-label {
        font-size: 0.8rem;
        opacity: 0.8;
        text-align: center;
    }

    .pill-value {
        font-size: 1.3rem;
        font-weight: 700;
        color: var(--blue-400, #60a5fa);
    }

    .reasons-block {
        margin-top: 18px;
        padding: 12px 14px;
        border-radius: 10px;
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(148, 163, 184, 0.3);
        font-size: 0.8rem;
    }

    .reasons-title {
        font-weight: 600;
        margin-bottom: 6px;
        color: #e5e7eb;
    }

    .reasons-block ul {
        margin: 0;
        padding-left: 18px;
        color: #cbd5f5;
    }

    .reasons-block li {
        margin-bottom: 2px;
    }

    .model-breakdown {
        margin-top: 24px;
        padding-top: 24px;
        border-top: 1px solid rgba(139, 92, 246, 0.2);
        animation: breakdownEnter var(--duration-fast, 100ms) var(--ease-out-smooth, cubic-bezier(0.22, 1, 0.36, 1));
    }

    @keyframes breakdownEnter {
        from {
            opacity: 0;
            transform: translateY(-8px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .model-breakdown h4 {
        margin: 0 0 16px 0;
        font-size: 1rem;
        opacity: 0.9;
    }

    .breakdown-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 12px;
        margin-bottom: 12px;
    }

    .model-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 12px;
    }

    .model-name {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
        opacity: 0.7;
    }

    .model-probs {
        display: flex;
        justify-content: space-between;
        gap: 8px;
    }

    .prob-mini {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 4px;
        font-size: 0.75rem;
    }

    .prob-mini span:first-child {
        opacity: 0.6;
        font-size: 0.7rem;
    }

    .prob-mini span:last-child {
        font-weight: 700;
    }

    .breakdown-note {
        font-size: 0.75rem;
        opacity: 0.6;
        text-align: center;
        font-style: italic;
    }

    @media (max-width: 640px) {
        .additional-predictions {
            grid-template-columns: 1fr;
        }

        .breakdown-grid {
            grid-template-columns: 1fr;
        }
    }
</style>
