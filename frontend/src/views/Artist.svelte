<script>
  import Hero from '../components/Hero.svelte';
  import Icon from '../components/Icon.svelte';
  import Card from '../components/Card.svelte';
  import RefList from '../components/RefList.svelte';
  import { browse, playUris, shuffleUris } from '../lib/library.js';
  import { artUrl } from '../lib/art.svelte.js';
  import { href, route } from '../lib/router.svelte.js';
  import { plural, sourceName } from '../lib/format.js';
  import { collectionSheet } from '../lib/actions.js';
  import { openSheet } from '../lib/ui.svelte.js';

  const uri = $derived(route.params.uri);
  const name = $derived(route.params.name || 'Artist');
  const refsPromise = $derived(uri ? browse(uri) : Promise.resolve([]));
</script>

<div class="page">
  {#await refsPromise}
    <div class="spinner"></div>
  {:then refs}
    {@const albums = refs.filter((r) => r.type === 'album')}
    {@const tracks = refs.filter((r) => r.type === 'track')}
    {@const other = refs.filter((r) => r.type !== 'album' && r.type !== 'track')}
    {@const playable = albums.length ? albums.map((a) => a.uri) : [uri]}
    <Hero
      image={artUrl(uri, { kind: 'artist', size: 512, artist: name })}
      label="Artist · {sourceName(uri)}"
      title={name}
      round
      icon="artist"
    >
      {#if albums.length}{plural(albums.length, 'album')}{/if}
      {#if tracks.length}{albums.length ? ' · ' : ''}{plural(tracks.length, 'track')}{/if}

      {#snippet actions()}
        <button class="btn primary" onclick={() => playUris(playable)}>
          <Icon name="play" size={20} /> Play
        </button>
        <button class="btn" onclick={() => shuffleUris(playable)}>
          <Icon name="shuffle" size={20} /> Shuffle
        </button>
        <button
          class="icon-btn"
          aria-label="More"
          onclick={() => openSheet(collectionSheet({ uri, name, kind: 'artist', uris: playable }))}
        >
          <Icon name="more" />
        </button>
      {/snippet}
    </Hero>

    {#if albums.length}
      <h2 class="section-title">Albums</h2>
      <div class="grid">
        {#each albums as a (a.uri)}
          <Card
            href={href('/album', { uri: a.uri, name: a.name })}
            image={artUrl(a.uri, { kind: 'album', size: 256, artist: name, album: a.name })}
            title={a.name}
            onplay={() => playUris([a.uri])}
            sheet={() => collectionSheet({ uri: a.uri, name: a.name, subtitle: name })}
          />
        {/each}
      </div>
    {/if}
    {#if tracks.length || other.length}
      <h2 class="section-title">{albums.length ? 'More' : 'Tracks'}</h2>
      <RefList refs={[...other, ...tracks]} />
    {/if}
    {#if !refs.length}
      <div class="empty">Nothing found for this artist.</div>
    {/if}
  {:catch e}
    <div class="empty">Could not load artist: {e.message}</div>
  {/await}
</div>
