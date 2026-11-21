<script>
  let { size = 32 } = $props();
</script>

<svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
  <defs>
    <linearGradient id="melody-logo" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="var(--accent)" />
      <stop offset="1" stop-color="color-mix(in srgb, var(--accent) 55%, #ec4899)" />
    </linearGradient>
  </defs>
  <rect width="64" height="64" rx="16" fill="url(#melody-logo)" />
  <g fill="#fff">
    <circle cx="22" cy="44" r="7" />
    <circle cx="42" cy="39" r="7" />
    <rect x="25" y="19" width="4" height="25" />
    <rect x="45" y="14" width="4" height="25" />
    <polygon points="25,17 49,11 49,18 25,24" />
  </g>
</svg>
