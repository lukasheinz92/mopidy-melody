<script>
  // Generic list of Mopidy Refs (directories, tracks, playlists, ...).
  // Tracks are rendered from their Ref only - no lookup needed, so this is
  // fast even for big folders or radio station lists.
  import Cover from './Cover.svelte';
  import Icon from './Icon.svelte';
  import { href } from '../lib/router.svelte.js';
  import { tapTrack } from '../lib/library.js';
  import { artUrl } from '../lib/art.svelte.js';
  import { trackSheet } from '../lib/actions.js';
  import { openSheet } from '../lib/ui.svelte.js';
  import { player } from '../lib/player.svelte.js';

  let { refs = [], images = false, limit = Infinity } = $props();

  const ICONS = { directory: 'folder', playlist: 'playlist', album: 'album', artist: 'artist' };

  function link(ref) {
    if (ref.type === 'album') return href('/album', { uri: ref.uri, name: ref.name });
    if (ref.type === 'artist') return href('/artist', { uri: ref.uri, name: ref.name });
    if (ref.type === 'playlist') return href('/playlist', { uri: ref.uri, name: ref.name });
    return href('/browse', { uri: ref.uri, name: ref.name });
  }

  function more(e, ref) {
    e.preventDefault();
    e.stopPropagation();
    openSheet(trackSheet({ uri: ref.uri, name: ref.name }));
  }
</script>

<div class="list">
  {#each refs.slice(0, limit) as ref (ref.uri)}
    {#if ref.type === 'track'}
      <div
        class="row"
        class:current={player.tlTrack?.track?.uri === ref.uri}
        role="button"
        tabindex="0"
        onclick={() => tapTrack(ref.uri)}
        onkeydown={(e) => e.key === 'Enter' && tapTrack(ref.uri)}
        oncontextmenu={(e) => more(e, ref)}
      >
        <div class="ic">
          {#if images}<Cover src={artUrl(ref.uri, { size: 96 })} icon="note" />{:else}<Icon name="note" />{/if}
        </div>
        <div class="name ellipsis">{ref.name}</div>
        <button class="icon-btn" aria-label="More" onclick={(e) => more(e, ref)}>
          <Icon name="more" size={20} />
        </button>
      </div>
    {:else}
      <a class="row" href={link(ref)}>
        <div class="ic">
          {#if images}
            <Cover src={artUrl(ref.uri, { size: 96 })} icon={ICONS[ref.type] || 'folder'} />
          {:else}
            <Icon name={ICONS[ref.type] || 'folder'} />
          {/if}
        </div>
        <div class="name ellipsis">{ref.name}</div>
        <Icon name="chevronRight" size={20} class="chev" />
      </a>
    {/if}
  {/each}
</div>

<style>
  .list {
    display: flex;
    flex-direction: column;
  }
  .row {
    display: flex;
    align-items: center;
    gap: 14px;
    min-height: 56px;
    padding: 6px 6px 6px 10px;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: background 0.12s;
  }
  .row:hover {
    background: var(--surface-hover);
  }
  .row.current .name {
    color: var(--accent-text);
  }
  .ic {
    display: grid;
    place-items: center;
    width: 42px;
    height: 42px;
    border-radius: 8px;
    background: var(--surface-2);
    color: var(--text-2);
    flex-shrink: 0;
    overflow: hidden;
  }
  .ic :global(.cover) {
    border-radius: 0;
  }
  .name {
    flex: 1;
    font-weight: 550;
  }
  .row :global(.chev) {
    color: var(--text-3);
    margin-right: 8px;
  }
</style>
