<script>
  // Album / artist / playlist tile with hover play button.
  import Cover from './Cover.svelte';
  import Icon from './Icon.svelte';
  import { openSheet } from '../lib/ui.svelte.js';

  let { href, image, title, subtitle = '', round = false, icon = 'album', onplay, sheet } = $props();

  function context(e) {
    if (!sheet) return;
    e.preventDefault();
    openSheet(sheet());
  }
</script>

<a class="card" {href} oncontextmenu={context}>
  <div class="art" class:round-art={round}>
    <Cover src={image} {round} {icon} alt={title} />
    {#if onplay}
      <button
        class="play"
        aria-label="Play {title}"
        onclick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onplay();
        }}
      >
        <Icon name="play" size={26} />
      </button>
    {/if}
  </div>
  <div class="title ellipsis" class:center={round}>{title}</div>
  {#if subtitle}
    <div class="subtitle ellipsis" class:center={round}>{subtitle}</div>
  {/if}
</a>

<style>
  .card {
    display: block;
    padding: 10px;
    margin: -10px;
    border-radius: var(--radius);
    transition: background 0.2s;
    min-width: 0;
  }
  .card:hover {
    background: var(--surface-hover);
  }
  .art {
    position: relative;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
    border-radius: var(--radius-sm);
  }
  .art.round-art {
    border-radius: 50%;
  }
  .play {
    position: absolute;
    right: 8px;
    bottom: 8px;
    width: 46px;
    height: 46px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    background: var(--accent);
    color: #fff;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.4);
    opacity: 0;
    transform: translateY(8px);
    transition:
      opacity 0.2s,
      transform 0.25s var(--ease);
  }
  .card:hover .play,
  .play:focus-visible {
    opacity: 1;
    transform: none;
  }
  .play:hover {
    transform: scale(1.06) !important;
  }
  @media (hover: none) {
    .play {
      display: none;
    }
  }
  .title {
    margin-top: 10px;
    font-weight: 600;
    font-size: 14.5px;
  }
  .subtitle {
    margin-top: 2px;
    font-size: 13px;
    color: var(--text-2);
  }
  .center {
    text-align: center;
  }
</style>
