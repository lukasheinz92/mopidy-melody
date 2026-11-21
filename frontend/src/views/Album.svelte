<script>
  import Hero from '../components/Hero.svelte';
  import Icon from '../components/Icon.svelte';
  import TrackList from '../components/TrackList.svelte';
  import { lookup, playUris, shuffleUris } from '../lib/library.js';
  import { artUrl } from '../lib/art.svelte.js';
  import { href, route } from '../lib/router.svelte.js';
  import { longDuration, year, plural, sourceName } from '../lib/format.js';
  import { collectionSheet } from '../lib/actions.js';
  import { openSheet } from '../lib/ui.svelte.js';

  const uri = $derived(route.params.uri);
  const tracksPromise = $derived(uri ? lookup(uri) : Promise.resolve([]));
</script>

<div class="page">
  {#await tracksPromise}
    <div class="spinner"></div>
  {:then tracks}
    {@const album = tracks[0]?.album}
    {@const artists = album?.artists?.length ? album.artists : tracks[0]?.artists || []}
    {@const name = album?.name || route.params.name || 'Album'}
    {@const total = tracks.reduce((s, t) => s + (t.length || 0), 0)}
    <Hero
      image={artUrl(uri, { kind: 'album', size: 512, artist: artists[0]?.name, album: name })}
      label="Album · {sourceName(uri)}"
      title={name}
    >
      {#each artists as a, i (a.uri || a.name)}
        {#if i}, {/if}
        {#if a.uri}<a href={href('/artist', { uri: a.uri, name: a.name })}>{a.name}</a>{:else}{a.name}{/if}
      {/each}
      {#if year(album?.date || tracks[0]?.date)}· {year(album?.date || tracks[0]?.date)}{/if}
      · {plural(tracks.length, 'song')}{#if total}, {longDuration(total)}{/if}

      {#snippet actions()}
        <button class="btn primary" onclick={() => playUris(tracks.map((t) => t.uri))}>
          <Icon name="play" size={20} /> Play
        </button>
        <button class="btn" onclick={() => shuffleUris(tracks.map((t) => t.uri))}>
          <Icon name="shuffle" size={20} /> Shuffle
        </button>
        <button
          class="icon-btn"
          aria-label="More"
          onclick={() =>
            openSheet(
              collectionSheet({
                uri,
                name,
                kind: 'album',
                subtitle: artists.map((a) => a.name).join(', '),
                uris: tracks.map((t) => t.uri),
              })
            )}
        >
          <Icon name="more" />
        </button>
      {/snippet}
    </Hero>
    {#if tracks.length}
      <TrackList {tracks} numbered discs album={false} />
    {:else}
      <div class="empty">This album has no playable tracks.</div>
    {/if}
  {:catch e}
    <div class="empty">Could not load album: {e.message}</div>
  {/await}
</div>
