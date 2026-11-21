<script>
  import Icon from './Icon.svelte';

  let { src, alt = '', icon = 'album', round = false, eager = false, class: cls = '' } = $props();
  let loaded = $state(false);
  let failed = $state(false);

  $effect(() => {
    src;
    loaded = false;
    failed = false;
  });
</script>

<div class="cover {cls}" class:round>
  {#if src && !failed}
    <img
      {src}
      {alt}
      loading={eager ? 'eager' : 'lazy'}
      decoding="async"
      class:loaded
      onload={() => (loaded = true)}
      onerror={() => (failed = true)}
    />
  {/if}
  {#if !loaded}
    <div class="fallback"><Icon name={icon} size={40} /></div>
  {/if}
</div>

<style>
  .cover {
    position: relative;
    aspect-ratio: 1;
    width: 100%;
    border-radius: var(--radius-sm);
    overflow: hidden;
    background: var(--placeholder);
    flex-shrink: 0;
  }
  .round {
    border-radius: 50%;
  }
  img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: 0;
    transition: opacity 0.3s;
  }
  img.loaded {
    opacity: 1;
  }
  .fallback {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    color: var(--text-3);
  }
  .fallback :global(svg) {
    width: 38%;
    height: 38%;
    max-width: 64px;
    max-height: 64px;
  }
</style>
