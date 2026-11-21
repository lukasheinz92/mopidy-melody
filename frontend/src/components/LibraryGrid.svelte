<script>
  // Albums / Artists overview: one chip per configured source (+ "All").
  import Card from './Card.svelte';
  import Icon from './Icon.svelte';
  import LibraryHeader from './LibraryHeader.svelte';
  import { browse, lookupMany, playUris } from '../lib/library.js';
  import { player } from '../lib/player.svelte.js';
  import { settings } from '../lib/settings.svelte.js';
  import { artUrl } from '../lib/art.svelte.js';
  import { href } from '../lib/router.svelte.js';
  import { scheme, sourceName, artistNames, year } from '../lib/format.js';
  import { collectionSheet } from '../lib/actions.js';
  import { toastError } from '../lib/toast.svelte.js';

  let { kind, title, uris = [] } = $props(); // kind: album | artist

  const PAGE = 120;
  const settingKey = $derived(kind === 'album' ? 'albumSource' : 'artistSource');

  const available = $derived(uris.filter((u) => player.uriSchemes.includes(scheme(u))));
  const chips = $derived(available.length > 1 ? [...available, 'all'] : available);
  const selected = $derived(chips.includes(settings[settingKey]) ? settings[settingKey] : chips[0]);

  let items = $state([]);
  let loading = $state(true);
  let filter = $state('');
  let limit = $state(PAGE);
  let meta = $state({}); // uri -> { artist, year } for local albums
  let sentinel = $state();

  $effect(() => {
    const source = selected;
    if (!source || !player.online) return;
    loading = true;
    limit = PAGE;
    const sources = source === 'all' ? available : [source];
    Promise.all(sources.map((u) => browse(u).catch(() => [])))
      .then((lists) => {
        if (selected !== source) return;
        const refs = lists.flat().filter((r) => r.type === kind || r.type === 'directory');
        if (source === 'all') refs.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
        items = refs;
      })
      .catch((e) => toastError(e))
      .finally(() => (loading = false));
  });

  const filtered = $derived.by(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (r) =>
        (r.name || '').toLowerCase().includes(q) ||
        (meta[r.uri]?.artist || '').toLowerCase().includes(q)
    );
  });
  const visible = $derived(filtered.slice(0, limit));

  // Local albums only carry a name; fetch artist/year for what's on screen.
  $effect(() => {
    if (kind !== 'album') return;
    const missing = visible
      .filter((r) => r.uri.startsWith('local:album') && !(r.uri in meta))
      .map((r) => r.uri);
    if (!missing.length) return;
    for (const u of missing) meta[u] = null;
    lookupMany(missing)
      .then((result) => {
        for (const [u, tracks] of Object.entries(result)) {
          const t = tracks[0];
          const artists = t?.album?.artists?.length ? t.album.artists : t?.artists;
          meta[u] = { artist: artistNames(artists), year: year(t?.album?.date || t?.date) };
        }
      })
      .catch(() => {});
  });

  // Infinite scroll.
  $effect(() => {
    if (!sentinel) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && limit < filtered.length) limit += PAGE;
      },
      { rootMargin: '800px' }
    );
    io.observe(sentinel);
    return () => io.disconnect();
  });

  function subtitle(ref) {
    if (kind === 'artist') return '';
    const m = meta[ref.uri];
    const parts = [m?.artist, m?.year].filter(Boolean);
    if (selected === 'all') parts.push(sourceName(ref.uri));
    return parts.join(' · ');
  }

  function link(ref) {
    // Mopidy-Local lists artists as directories (local:directory?albumartist=...).
    if (ref.type === 'directory' && kind !== 'artist')
      return href('/browse', { uri: ref.uri, name: ref.name });
    return href('/' + kind, { uri: ref.uri, name: ref.name });
  }
</script>

<div class="page">
  <LibraryHeader />
  <div class="page-header">
    <h1>{title}</h1>
    <div class="field search">
      <Icon name="search" size={18} />
      <input bind:value={filter} placeholder="Filter {title.toLowerCase()}" />
      {#if filter}
        <button onclick={() => (filter = '')} aria-label="Clear"><Icon name="close" size={18} /></button>
      {/if}
    </div>
  </div>

  {#if chips.length > 1}
    <div class="chips">
      {#each chips as chip (chip)}
        <button
          class="chip"
          class:active={chip === selected}
          onclick={() => (settings[settingKey] = chip)}
        >
          {chip === 'all' ? 'All' : sourceName(chip)}
        </button>
      {/each}
    </div>
  {/if}

  {#if loading && !items.length}
    <div class="spinner"></div>
  {:else if !available.length && player.uriSchemes.length}
    <div class="empty">
      <Icon name={kind} size={48} />
      <div>No library source available. Check <code>album_uris</code> / <code>artist_uris</code>.</div>
    </div>
  {:else if !filtered.length}
    <div class="empty"><Icon name={kind} size={48} /><div>Nothing here</div></div>
  {:else}
    <div class="count muted">{filtered.length} {title.toLowerCase()}</div>
    <div class="grid">
      {#each visible as ref (ref.uri)}
        <Card
          href={link(ref)}
          image={artUrl(ref.uri, {
            kind,
            size: 256,
            artist: kind === 'artist' ? ref.name : meta[ref.uri]?.artist,
            album: kind === 'album' ? ref.name : undefined,
          })}
          title={ref.name}
          subtitle={subtitle(ref)}
          round={kind === 'artist'}
          icon={kind}
          onplay={() => playUris([ref.uri])}
          sheet={() => collectionSheet({ uri: ref.uri, name: ref.name, kind, subtitle: subtitle(ref) })}
        />
      {/each}
    </div>
    <div bind:this={sentinel} class="sentinel"></div>
  {/if}
</div>

<style>
  .search {
    width: min(320px, 100%);
  }
  .search button {
    display: grid;
    color: var(--text-3);
  }
  .chips {
    margin-bottom: 18px;
  }
  .count {
    font-size: 13px;
    margin-bottom: 14px;
  }
  .sentinel {
    height: 1px;
  }
  @media (max-width: 799px) {
    .page-header h1 {
      display: none;
    }
    .search {
      width: 100%;
    }
  }
</style>
