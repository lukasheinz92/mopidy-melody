<script>
  // Top-level browse entries (one tile per backend), shown on the
  // Browse & Search page while the search field is empty.
  import Icon from './Icon.svelte';
  import { browse } from '../lib/library.js';
  import { href } from '../lib/router.svelte.js';
  import { player } from '../lib/player.svelte.js';
  import { scheme } from '../lib/format.js';

  const refsPromise = $derived(player.online ? browse(null) : new Promise(() => {}));

  // Root entries get a recognisable icon per backend.
  const ROOT_ICONS = {
    local: 'library',
    jellyfin: 'library',
    radiobrowser: 'radio',
    tunein: 'radio',
    youtube: 'playlist',
    invidious: 'playlist',
    m3u: 'playlist',
    file: 'folder',
  };
</script>

{#await refsPromise}
  <div class="spinner"></div>
{:then refs}
  <div class="roots">
    {#each refs as r (r.uri)}
      <a class="root" href={href('/browse', { uri: r.uri, name: r.name })}>
        <span class="ic"><Icon name={ROOT_ICONS[scheme(r.uri)] || 'folder'} size={26} /></span>
        <span class="ellipsis">{r.name}</span>
      </a>
    {/each}
  </div>
{:catch e}
  <div class="empty">Could not browse: {e.message}</div>
{/await}

<style>
  .roots {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 12px;
  }
  .root {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 14px;
    border-radius: var(--radius);
    background: var(--surface);
    border: 1px solid var(--border);
    font-weight: 650;
    transition:
      transform 0.15s var(--ease),
      background 0.15s;
  }
  .root:hover {
    background: var(--surface-2);
  }
  .root:active {
    transform: scale(0.98);
  }
  .ic {
    display: grid;
    place-items: center;
    width: 48px;
    height: 48px;
    border-radius: 12px;
    background: var(--accent-soft);
    color: var(--accent-text);
    flex-shrink: 0;
  }
  @media (max-width: 799px) {
    .roots {
      grid-template-columns: 1fr;
    }
  }
</style>
