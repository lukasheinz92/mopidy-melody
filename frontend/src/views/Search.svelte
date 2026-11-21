<script>
  // Browse & Search: searches every backend in parallel and shows results as
  // they arrive; with an empty search field it shows the browse sources.
  import Card from '../components/Card.svelte';
  import BrowseRoots from '../components/BrowseRoots.svelte';
  import Icon from '../components/Icon.svelte';
  import TrackList from '../components/TrackList.svelte';
  import { search, playUris, playNow } from '../lib/library.js';
  import { artUrl } from '../lib/art.svelte.js';
  import { href, route } from '../lib/router.svelte.js';
  import { player } from '../lib/player.svelte.js';
  import { sourceName, artistNames, year } from '../lib/format.js';
  import { collectionSheet } from '../lib/actions.js';

  import { untrack } from 'svelte';

  // Schemes that only play URLs or duplicate another backend.
  const SKIP = new Set(['http', 'https', 'mms', 'rtmp', 'rtmps', 'rtsp', 'file', 'm3u', 'yt']);
  const ORDER = ['local', 'jellyfin'];

  let query = $state(route.params.q || '');
  let source = $state(route.params.source || 'all');
  let results = $state({}); // scheme -> { loading, artists, albums, tracks, error }
  let input = $state();
  let lastSearch = '';
  let timer;

  const schemes = $derived(
    player.uriSchemes
      .filter((s) => !SKIP.has(s))
      .sort((a, b) => {
        const ia = ORDER.indexOf(a) + 1 || 99;
        const ib = ORDER.indexOf(b) + 1 || 99;
        return ia - ib || a.localeCompare(b);
      })
  );

  function run(force = false) {
    const q = query.trim();
    if (q.length < 2 || !schemes.length) return;
    const key = q + '|' + source;
    if (!force && key === lastSearch) return;
    lastSearch = key;
    history.replaceState(null, '', href('/search', { q, source: source === 'all' ? null : source }));
    const targets = source === 'all' ? schemes : [source];
    results = Object.fromEntries(targets.map((s) => [s, { loading: true }]));
    for (const s of targets) {
      search(q, s)
        .then((list) => {
          if (lastSearch !== key) return;
          const merged = { artists: [], albums: [], tracks: [] };
          for (const r of list || []) {
            merged.artists.push(...(r.artists || []));
            merged.albums.push(...(r.albums || []));
            merged.tracks.push(...(r.tracks || []));
          }
          results[s] = merged;
        })
        .catch((e) => {
          if (lastSearch === key) results[s] = { error: e.message, artists: [], albums: [], tracks: [] };
        });
    }
  }

  function typed() {
    clearTimeout(timer);
    if (!query.trim()) {
      // Cleared: back to browsing.
      lastSearch = '';
      results = {};
      history.replaceState(null, '', href('/browse'));
      return;
    }
    timer = setTimeout(run, 500);
  }

  $effect(() => {
    // Run once schemes are known (e.g. when opening a shared #/search?q= link).
    if (schemes.length) untrack(() => query && run());
  });

  // Focus only when search was asked for (the "/" shortcut, a #/search link);
  // opening the page on a phone shouldn't pop up the keyboard.
  $effect(() => {
    if (!query && route.path === '/search') input?.focus();
  });

  const entries = $derived(Object.entries(results));
  const loading = $derived(entries.some(([, r]) => r.loading));
  const artists = $derived(entries.flatMap(([, r]) => (r.artists || []).slice(0, 12)).filter((a) => a.uri));
  const albums = $derived(entries.flatMap(([, r]) => (r.albums || []).slice(0, 18)).filter((a) => a.uri));
  const trackGroups = $derived(entries.filter(([, r]) => r.tracks?.length));
  const nothing = $derived(
    !loading && entries.length && !artists.length && !albums.length && !trackGroups.length
  );
</script>

<div class="page">
  <div class="page-header"><h1>Browse & Search</h1></div>
  <form class="field big" onsubmit={(e) => { e.preventDefault(); run(true); }}>
    <Icon name="search" size={22} />
    <input
      bind:this={input}
      bind:value={query}
      oninput={typed}
      placeholder="Artists, albums, songs, radio…"
      enterkeyhint="search"
      type="search"
    />
    {#if loading}<span class="mini-spin"></span>{/if}
  </form>

  {#if entries.length}
    <div class="chips">
      {#each ['all', ...schemes] as s (s)}
        <button
          class="chip"
          class:active={source === s}
          onclick={() => {
            source = s;
            run(true);
          }}>{s === 'all' ? 'All' : sourceName(s)}</button
        >
      {/each}
    </div>
  {/if}

  {#if artists.length}
    <h2 class="section-title">Artists</h2>
    <div class="grid">
      {#each artists.slice(0, 12) as a (a.uri)}
        <Card
          href={href('/artist', { uri: a.uri, name: a.name })}
          image={artUrl(a.uri, { kind: 'artist', artist: a.name })}
          title={a.name}
          subtitle={sourceName(a.uri)}
          round
          icon="artist"
        />
      {/each}
    </div>
  {/if}

  {#if albums.length}
    <h2 class="section-title">Albums</h2>
    <div class="grid">
      {#each albums.slice(0, 24) as a (a.uri)}
        <Card
          href={href('/album', { uri: a.uri, name: a.name })}
          image={artUrl(a.uri, { kind: 'album', artist: a.artists?.[0]?.name, album: a.name })}
          title={a.name}
          subtitle={[artistNames(a.artists), year(a.date), source === 'all' ? sourceName(a.uri) : '']
            .filter(Boolean)
            .join(' · ')}
          onplay={() => playUris([a.uri])}
          sheet={() => collectionSheet({ uri: a.uri, name: a.name, subtitle: artistNames(a.artists) })}
        />
      {/each}
    </div>
  {/if}

  {#each trackGroups as [s, r] (s)}
    <h2 class="section-title">
      Songs {#if trackGroups.length > 1 || source === 'all'}<span class="badge">{sourceName(s)}</span>{/if}
    </h2>
    <!-- A tap plays just that song: queueing the whole result list means a
         slow lookup for every hit on remote backends (YouTube, Invidious). -->
    <TrackList tracks={r.tracks.slice(0, 50)} quick ontap={(t) => playNow([t.uri])} />
  {/each}

  {#each entries.filter(([, r]) => r.error) as [s, r] (s)}
    <div class="error muted">{sourceName(s)}: {r.error}</div>
  {/each}

  {#if nothing}
    <div class="empty"><Icon name="search" size={48} /><div>No results for “{query}”</div></div>
  {:else if !entries.length}
    <BrowseRoots />
  {/if}
</div>

<style>
  .big {
    height: 52px;
    margin-bottom: 14px;
    font-size: 16px;
  }
  .big input::-webkit-search-cancel-button {
    filter: grayscale(1);
  }
  .mini-spin {
    width: 18px;
    height: 18px;
    border-radius: 50%;
    border: 2px solid var(--surface);
    border-top-color: var(--accent);
    animation: spin 0.8s linear infinite;
  }
  .section-title {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .error {
    font-size: 13px;
    margin-top: 12px;
  }
</style>
