<script>
  import Hero from '../components/Hero.svelte';
  import Icon from '../components/Icon.svelte';
  import TrackList from '../components/TrackList.svelte';
  import {
    playlist,
    playUris,
    shuffleUris,
    deletePlaylist,
    removeFromPlaylist,
    isEditablePlaylist,
  } from '../lib/library.js';
  import { artUrl } from '../lib/art.svelte.js';
  import { route } from '../lib/router.svelte.js';
  import { player } from '../lib/player.svelte.js';
  import { longDuration, plural, sourceName } from '../lib/format.js';
  import { confirm, openSheet } from '../lib/ui.svelte.js';
  import { collectionSheet } from '../lib/actions.js';
  import { toast, toastError } from '../lib/toast.svelte.js';

  const uri = $derived(route.params.uri);
  const editable = $derived(isEditablePlaylist(uri));
  const plPromise = $derived(
    uri && player.online ? (player.playlistsVersion, playlist(uri)) : new Promise(() => {})
  );

  async function remove(pl) {
    const ok = await confirm({
      title: 'Delete playlist?',
      message: `“${pl.name}” will be deleted permanently.`,
      confirmLabel: 'Delete',
      danger: true,
    });
    if (!ok) return;
    try {
      await deletePlaylist(pl.uri);
      toast('Playlist deleted');
      history.back();
    } catch (e) {
      toastError(e);
    }
  }

  function trackActions(pl) {
    if (!editable) return undefined;
    return (track, index) => [
      {
        icon: 'delete',
        label: 'Remove from playlist',
        danger: true,
        run: () => removeFromPlaylist(pl, index).catch((e) => toastError(e)),
      },
    ];
  }
</script>

<div class="page">
  {#await plPromise}
    <div class="spinner"></div>
  {:then pl}
    {#if pl}
      {@const tracks = pl.tracks || []}
      {@const uris = tracks.map((t) => t.uri)}
      {@const total = tracks.reduce((s, t) => s + (t.length || 0), 0)}
      <Hero
        image={artUrl(uri, { kind: 'playlist', size: 512 })}
        label="Playlist · {sourceName(uri)}"
        title={pl.name}
        icon="playlist"
      >
        {plural(tracks.length, 'song')}{#if total}, {longDuration(total)}{/if}
        {#snippet actions()}
          <button class="btn primary" disabled={!tracks.length} onclick={() => playUris(uris)}>
            <Icon name="play" size={20} /> Play
          </button>
          <button class="btn" disabled={!tracks.length} onclick={() => shuffleUris(uris)}>
            <Icon name="shuffle" size={20} /> Shuffle
          </button>
          <button
            class="icon-btn"
            aria-label="More"
            onclick={() =>
              openSheet({
                ...collectionSheet({ uri, name: pl.name, kind: 'playlist', uris }),
                actions: [
                  ...collectionSheet({ uri, name: pl.name, kind: 'playlist', uris }).actions,
                  ...(editable
                    ? [{ icon: 'delete', label: 'Delete playlist', danger: true, run: () => remove(pl) }]
                    : []),
                ],
              })}
          >
            <Icon name="more" />
          </button>
        {/snippet}
      </Hero>
      {#if tracks.length}
        <TrackList {tracks} extraActions={trackActions(pl)} />
      {:else}
        <div class="empty">This playlist is empty. Add songs from their “⋮” menu.</div>
      {/if}
    {:else}
      <div class="empty">Playlist not found.</div>
    {/if}
  {:catch e}
    <div class="empty">Could not load playlist: {e.message}</div>
  {/await}
</div>
