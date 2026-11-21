<script>
  import Sidebar from './components/Sidebar.svelte';
  import TabBar from './components/TabBar.svelte';
  import PlayerBar from './components/PlayerBar.svelte';
  import MiniPlayer from './components/MiniPlayer.svelte';
  import NowPlaying from './components/NowPlaying.svelte';
  import Sheet from './components/Sheet.svelte';
  import Dialogs from './components/Dialogs.svelte';
  import Toasts from './components/Toasts.svelte';
  import CoverPicker from './components/CoverPicker.svelte';
  import Icon from './components/Icon.svelte';
  import LibraryGrid from './components/LibraryGrid.svelte';
  import Album from './views/Album.svelte';
  import Artist from './views/Artist.svelte';
  import Browse from './views/Browse.svelte';
  import Search from './views/Search.svelte';
  import Playlists from './views/Playlists.svelte';
  import Playlist from './views/Playlist.svelte';
  import Queue from './views/Queue.svelte';
  import Rooms from './views/Rooms.svelte';
  import Settings from './views/Settings.svelte';
  import { route } from './lib/router.svelte.js';
  import { navItems } from './lib/nav.js';
  import { prefs, loadPrefs } from './lib/prefs.svelte.js';
  import { player, controls, currentTrack } from './lib/player.svelte.js';
  import { ui } from './lib/ui.svelte.js';
  import { rpc } from './lib/rpc.js';
  import { getConfig } from './lib/api.js';
  import { trackTitle, trackArtist } from './lib/format.js';
  import { trackArt, loadArtOverrides } from './lib/art.svelte.js';

  let config = $state(null);
  getConfig().then((c) => (config = c));
  loadPrefs();
  loadArtOverrides();
  rpc.connect();

  // The start page is the first menu item.
  const home = $derived(navItems(config)[0]?.path || '/browse');
  $effect(() => {
    if (route.path === '/' && prefs.loaded && config) location.replace('#' + home);
  });

  // Window title follows the current track.
  $effect(() => {
    const t = currentTrack();
    const name = config?.title || 'Melody';
    document.title =
      t && player.state === 'playing'
        ? `${player.streamTitle || trackTitle(t)} · ${trackArtist(t) || name}`
        : name;
  });

  // Lock-screen / headset controls.
  $effect(() => {
    if (!('mediaSession' in navigator)) return;
    const t = currentTrack();
    if (!t) return;
    const art = trackArt(t, 512);
    navigator.mediaSession.metadata = new MediaMetadata({
      title: player.streamTitle || trackTitle(t),
      artist: trackArtist(t),
      album: t.album?.name || '',
      artwork: art ? [{ src: new URL(art, location.href).href, sizes: '512x512', type: 'image/jpeg' }] : [],
    });
    navigator.mediaSession.playbackState = player.state === 'playing' ? 'playing' : 'paused';
  });
  if ('mediaSession' in navigator) {
    const ms = navigator.mediaSession;
    ms.setActionHandler('play', () => controls.toggle());
    ms.setActionHandler('pause', () => controls.toggle());
    ms.setActionHandler('previoustrack', () => controls.previous());
    ms.setActionHandler('nexttrack', () => controls.next());
    ms.setActionHandler('stop', () => controls.stop());
  }

  // Keyboard shortcuts (desktop).
  function keydown(e) {
    if (e.target.closest('input, select, textarea, [contenteditable]')) return;
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (e.code === 'Space') {
      e.preventDefault();
      controls.toggle();
    } else if (e.key === 'ArrowRight' && e.shiftKey) controls.next();
    else if (e.key === 'ArrowLeft' && e.shiftKey) controls.previous();
    else if (e.key === '/') {
      e.preventDefault();
      location.hash = '#/search';
    }
  }
</script>

<svelte:window onkeydown={keydown} />

<div class="app" class:queue-open={ui.queuePanel}>
  <aside class="side"><Sidebar {config} /></aside>

  <main>
    {#if !player.online && !player.connecting}
      <div class="banner"><Icon name="offline" size={18} /> Connection to Mopidy lost — reconnecting…</div>
    {/if}
    {#key route.path + JSON.stringify(route.params)}
      {#if route.path === '/albums'}
        <LibraryGrid kind="album" title="Albums" uris={config?.album_uris || []} />
      {:else if route.path === '/artists'}
        <LibraryGrid kind="artist" title="Artists" uris={config?.artist_uris || []} />
      {:else if route.path === '/album'}
        <Album />
      {:else if route.path === '/artist'}
        <Artist />
      {:else if route.path === '/browse' && route.params.uri}
        <Browse />
      {:else if route.path === '/browse' || route.path === '/search'}
        <Search />
      {:else if route.path === '/playlists'}
        <Playlists />
      {:else if route.path === '/playlist'}
        <Playlist />
      {:else if route.path === '/queue'}
        <Queue />
      {:else if route.path === '/rooms'}
        <Rooms />
      {:else if route.path === '/settings'}
        <Settings {config} />
      {:else if route.path !== '/'}
        <div class="empty">Page not found. <a class="btn" href={'#' + home}>Go to start</a></div>
      {/if}
    {/key}
  </main>

  {#if ui.queuePanel}
    <aside class="queue-panel"><Queue panel /></aside>
  {/if}

  <div class="bottom">
    <div class="desktop-only"><PlayerBar {config} /></div>
    <div class="mobile-only">
      <MiniPlayer />
      <TabBar {config} />
    </div>
  </div>
</div>

{#if ui.nowPlaying}
  <NowPlaying {config} />
{/if}
<Sheet />
<Dialogs />
<CoverPicker />
<Toasts />

<style>
  .app {
    display: grid;
    grid-template-columns: var(--sidebar-w) minmax(0, 1fr);
    grid-template-rows: minmax(0, 1fr) auto;
    grid-template-areas:
      'side main'
      'bottom bottom';
    height: 100dvh;
  }
  .app.queue-open {
    grid-template-columns: var(--sidebar-w) minmax(0, 1fr) var(--queue-w);
    grid-template-areas:
      'side main queue'
      'bottom bottom bottom';
  }
  .side {
    grid-area: side;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .side :global(nav) {
    flex: 1;
  }
  main {
    grid-area: main;
    overflow-y: auto;
    overflow-x: hidden;
    min-height: 0;
    position: relative;
  }
  .queue-panel {
    grid-area: queue;
    overflow-y: auto;
    border-left: 1px solid var(--border);
    background: var(--bg-elev);
    min-height: 0;
  }
  .bottom {
    grid-area: bottom;
  }
  .mobile-only {
    display: none;
  }
  .banner {
    position: sticky;
    top: 0;
    z-index: 10;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 8px;
    background: #ef4444;
    color: #fff;
    font-size: 13.5px;
    font-weight: 600;
  }
  @media (max-width: 1100px) {
    .app.queue-open {
      grid-template-columns: var(--sidebar-w) minmax(0, 1fr);
      grid-template-areas:
        'side main'
        'bottom bottom';
    }
    .queue-panel {
      display: none;
    }
  }
  @media (max-width: 799px) {
    .app,
    .app.queue-open {
      grid-template-columns: minmax(0, 1fr);
      grid-template-areas:
        'main'
        'bottom';
    }
    .side,
    .queue-panel,
    .desktop-only {
      display: none;
    }
    .mobile-only {
      display: block;
      background: linear-gradient(transparent, var(--bg) 30%);
    }
  }
</style>
