<script>
  // Confidence Badge Component
  // Shows visual confidence level with color coding
  export let confidence = 0; // 0-1 probability
  export let size = "md"; // sm, md, lg
  export let showLabel = true;
  export let showIcon = true;

  $: confidencePercent = confidence * 100;

  $: level = confidencePercent >= 70 ? "high" : confidencePercent >= 50 ? "medium" : "low";

  $: labelText = level === "high" ? "High Confidence" : level === "medium" ? "Medium" : "Low Confidence";

  $: icon = level === "high" ? "🎯" : level === "medium" ? "📊" : "⚠️";

  $: sizeClasses = {
    sm: "text-xs px-2 py-0.5",
    md: "text-sm px-3 py-1",
    lg: "text-base px-4 py-1.5"
  }[size];

  $: colorClasses = {
    high: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    medium: "bg-amber-500/20 text-amber-400 border-amber-500/30",
    low: "bg-red-500/20 text-red-400 border-red-500/30"
  }[level];

  $: dotColor = {
    high: "bg-emerald-400",
    medium: "bg-amber-400",
    low: "bg-red-400"
  }[level];
</script>

<span class="inline-flex items-center gap-1.5 rounded-full border font-medium {sizeClasses} {colorClasses}">
  {#if showIcon}
    <span class="text-base">{icon}</span>
  {:else}
    <span class="relative flex h-2 w-2">
      <span class="animate-ping absolute inline-flex h-full w-full rounded-full {dotColor} opacity-75"></span>
      <span class="relative inline-flex rounded-full h-2 w-2 {dotColor}"></span>
    </span>
  {/if}
  {#if showLabel}
    <span>{labelText}</span>
  {/if}
  <span class="font-bold">{confidencePercent.toFixed(0)}%</span>
</span>
