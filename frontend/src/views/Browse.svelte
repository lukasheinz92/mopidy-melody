<script>
  import Card from '../components/Card.svelte';
  import Icon from '../components/Icon.svelte';
  import RefList from '../components/RefList.svelte';
  import { browse, playUris, search } from '../lib/library.js';
  import { artUrl } from '../lib/art.svelte.js';
  import { href, route } from '../lib/router.svelte.js';
  import { player } from '../lib/player.svelte.js';
  import { collectionSheet } from '../lib/actions.js';
  import { scheme, sourceName } from '../lib/format.js';

  // Folder view; the top level is part of the Browse & Search page.
  const uri = $derived(route.params.uri || null);
  const name = $derived(route.params.name || 'Browse');
  const refsPromise = $derived(player.online ? browse(uri) : new Promise(() => {}));

  let filter = $state('');
  $effect(() => {
    uri;
    filter = '';
  });

  function match(r) {
    return !filter || (r.name || '').toLowerCase().includes(filter.toLowerCase());
  }

  // The filter only sees this folder's entries; also search the folder's
  // backend, so e.g. a station can be found from RadioBrowser's top level.
  // file: folders have no search.
  const source = $derived(uri && scheme(uri) !== 'file' ? scheme(uri) : null);
  let found = $state(null); // null: no search; [] while loading or nothing found
  let searching = $state(false);
  $effect(() => {
    const q = filter.trim();
    const s = source;
    found = null;
    if (!s || q.length < 2) return;
    let stale = false;
    const timer = setTimeout(async () => {
      searching = true;
      try {
        const list = await search(q, s);
        if (stale) return;
        const seen = new Set();
        found = (list || [])
          .flatMap((r) => [
            ...(r.artists || []).map((a) => ({ type: 'artist', uri: a.uri, name: a.name })),
            ...(r.albums || []).map((a) => ({ type: 'album', uri: a.uri, name: a.name })),
            ...(r.tracks || []).map((t) => ({ type: 'track', uri: t.uri, name: t.name })),
          ])
          .filter((r) => r.uri && !seen.has(r.uri) && seen.add(r.uri))
          .slice(0, 100);
      } catch {
        if (!stale) found = [];
      } finally {
        if (!stale) searching = false;
      }
    }, 400);
    return () => {
      stale = true;
      searching = false;
      clearTimeout(timer);
    };
  });
</script>

<div class="page">
  <div class="page-header">
    <button class="icon-btn" onclick={() => history.back()} aria-label="Back"><Icon name="back" /></button>
    <h1>{name}</h1>
    <div class="field filter">
      <Icon name="search" size={18} />
      <input bind:value={filter} placeholder={source ? `Filter or search ${sourceName(source)}` : 'Filter'} />
      {#if searching}<span class="mini-spin"></span>{/if}
    </div>
  </div>

  {#await refsPromise}
    <div class="spinner"></div>
  {:then refs}
    {#if refs}
      {@const albums = refs.filter((r) => r.type === 'album' && match(r))}
      {@const artists = refs.filter((r) => r.type === 'artist' && match(r))}
      {@const rest = refs.filter((r) => r.type !== 'album' && r.type !== 'artist' && match(r))}
      {#if artists.length}
        {#if albums.length || rest.length}<h2 class="section-title">Artists</h2>{/if}
        <div class="grid">
          {#each artists as a (a.uri)}
            <Card
              href={href('/artist', { uri: a.uri, name: a.name })}
              image={artUrl(a.uri, { kind: 'artist', artist: a.name })}
              title={a.name}
              round
              icon="artist"
            />
          {/each}
        </div>
      {/if}
      {#if albums.length}
        {#if artists.length || rest.length}<h2 class="section-title">Albums</h2>{/if}
        <div class="grid">
          {#each albums as a (a.uri)}
            <Card
              href={href('/album', { uri: a.uri, name: a.name })}
              image={artUrl(a.uri, { kind: 'album', album: a.name })}
              title={a.name}
              onplay={() => playUris([a.uri])}
              sheet={() => collectionSheet({ uri: a.uri, name: a.name })}
            />
          {/each}
        </div>
      {/if}
      {#if rest.length}
        {#if artists.length || albums.length}<div style="height:24px"></div>{/if}
        <RefList refs={rest} images={rest.length <= 200 && rest.some((r) => r.type === 'track')} />
      {/if}
      {#if found?.length}
        <h2 class="section-title">Found in {sourceName(source)}</h2>
        <RefList refs={found} />
      {:else if found && !searching && !artists.length && !albums.length && !rest.length}
        <div class="empty"><Icon name="search" size={48} /><div>No results for “{filter.trim()}”</div></div>
      {/if}
      {#if !refs.length && !filter}
        <div class="empty"><Icon name="folder" size={48} /><div>This folder is empty</div></div>
      {/if}
    {/if}
  {:catch e}
    <div class="empty">Could not browse: {e.message}</div>
  {/await}
</div>

<style>
  .filter {
    width: min(300px, 100%);
  }
  .mini-spin {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
    border-radius: 50%;
    border: 2px solid var(--surface);
    border-top-color: var(--accent);
    animation: spin 0.8s linear infinite;
  }
  @media (max-width: 799px) {
    /* Own row under the title instead of squeezing next to it. */
    .filter {
      width: 100%;
    }
  }
</style>
