<script>
  import Card from '../components/Card.svelte';
  import Icon from '../components/Icon.svelte';
  import LibraryHeader from '../components/LibraryHeader.svelte';
  import { playlists, createPlaylist, playUris } from '../lib/library.js';
  import { artUrl } from '../lib/art.svelte.js';
  import { href, navigate } from '../lib/router.svelte.js';
  import { player } from '../lib/player.svelte.js';
  import { prompt } from '../lib/ui.svelte.js';
  import { sourceName } from '../lib/format.js';
  import { collectionSheet } from '../lib/actions.js';
  import { toastError } from '../lib/toast.svelte.js';

  const listPromise = $derived(
    player.online ? (player.playlistsVersion, playlists()) : new Promise(() => {})
  );

  async function create() {
    const name = await prompt({ title: 'New playlist', placeholder: 'Playlist name', confirmLabel: 'Create' });
    if (!name) return;
    try {
      const pl = await createPlaylist(name);
      navigate('/playlist', { uri: pl.uri, name: pl.name });
    } catch (e) {
      toastError(e, 'Could not create playlist');
    }
  }
</script>

<div class="page">
  <LibraryHeader />
  <div class="page-header">
    <h1>Playlists</h1>
    <button class="btn" onclick={create}><Icon name="add" size={20} /> New playlist</button>
  </div>

  {#await listPromise}
    <div class="spinner"></div>
  {:then list}
    {#if list.length}
      <div class="grid">
        {#each list as pl (pl.uri)}
          <Card
            href={href('/playlist', { uri: pl.uri, name: pl.name })}
            image={artUrl(pl.uri, { kind: 'playlist' })}
            title={pl.name}
            subtitle={sourceName(pl.uri)}
            icon="playlist"
            onplay={() => playUris([pl.uri])}
            sheet={() => collectionSheet({ uri: pl.uri, name: pl.name, kind: 'playlist' })}
          />
        {/each}
      </div>
    {:else}
      <div class="empty">
        <Icon name="playlist" size={48} />
        <div>No playlists yet. Save your queue or create one.</div>
      </div>
    {/if}
  {:catch e}
    <div class="empty">Could not load playlists: {e.message}</div>
  {/await}
</div>

<style>
  @media (max-width: 799px) {
    .page-header h1 {
      font-size: 0;
      flex: 1;
    }
    .page-header {
      justify-content: flex-end;
    }
  }
</style>
