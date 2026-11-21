<script>
  import Icon from '../components/Icon.svelte';
  import LocalScan from '../components/LocalScan.svelte';
  import { settings, ACCENTS } from '../lib/settings.svelte.js';
  import { player } from '../lib/player.svelte.js';
  import { clearArtCache } from '../lib/api.js';
  import { invalidate } from '../lib/library.js';
  import { toast, toastError } from '../lib/toast.svelte.js';
  import { sourceName } from '../lib/format.js';
  import { orderedItems, isHidden, TAB_COUNT } from '../lib/nav.js';
  import { prefs, persistPrefs } from '../lib/prefs.svelte.js';
  import { artState } from '../lib/art.svelte.js';

  let { config } = $props();

  const themes = [
    { id: 'system', label: 'System' },
    { id: 'light', label: 'Light' },
    { id: 'dark', label: 'Dark' },
  ];
  const tapActions = [
    { id: 'play', label: 'Play just this song (replace queue)' },
    { id: 'play-now', label: 'Play this track now (keep queue)' },
    { id: 'add', label: 'Add to queue' },
  ];

  async function clearArt() {
    try {
      const { cleared } = await clearArtCache();
      toast(`Cleared ${cleared} cached images`);
      setTimeout(() => location.reload(), 600);
    } catch (e) {
      toastError(e);
    }
  }

  const menu = $derived(orderedItems(config));
  // Position among visible items, to mark which ones fit in the mobile tab bar.
  const visibleIndex = $derived(menu.filter((i) => !isHidden(i)).map((i) => i.id));
  const visibleCount = $derived(visibleIndex.length);

  function move(index, delta) {
    const ids = menu.map((i) => i.id);
    const [id] = ids.splice(index, 1);
    ids.splice(index + delta, 0, id);
    prefs.nav.order = ids;
    persistPrefs();
  }

  function toggle(item) {
    prefs.nav.hidden = isHidden(item)
      ? prefs.nav.hidden.filter((id) => id !== item.id)
      : [...prefs.nav.hidden, item.id];
    persistPrefs();
  }

  function resetMenu() {
    prefs.nav = { order: [], hidden: [] };
    persistPrefs();
  }

  function reloadLibrary() {
    invalidate();
    toast('Library cache cleared');
  }
</script>

<div class="page narrow">
  <div class="page-header"><h1>Settings</h1></div>

  <section>
    <h2>Appearance</h2>
    <div class="row">
      <div class="label">Theme</div>
      <div class="seg">
        {#each themes as t (t.id)}
          <button class:active={settings.theme === t.id} onclick={() => (settings.theme = t.id)}>{t.label}</button>
        {/each}
      </div>
    </div>
    <div class="row">
      <div class="label">Accent colour</div>
      <div class="swatches">
        {#each ACCENTS as color (color)}
          <button
            class="swatch"
            class:active={settings.accent === color}
            style:background={color}
            onclick={() => (settings.accent = color)}
            aria-label="Accent {color}"
          >
            {#if settings.accent === color}<Icon name="check" size={16} />{/if}
          </button>
        {/each}
        <label class="swatch custom" title="Custom colour">
          <input type="color" bind:value={settings.accent} />
          <Icon name="edit" size={14} />
        </label>
      </div>
    </div>
  </section>

  <section>
    <h2>Menu</h2>
    <div class="hint menu-hint">
      Shared by all devices. On phones the first {TAB_COUNT} visible items are tabs{visibleCount >
      TAB_COUNT + 1
        ? ', the rest are under “More”'
        : ''}.
    </div>
    <div class="menu">
      {#each menu as item, i (item.id)}
        {@const hidden = isHidden(item)}
        {@const pos = visibleIndex.indexOf(item.id)}
        <div class="menu-row" class:hidden>
          <Icon name={item.icon} size={20} />
          <span class="menu-label">{item.label}</span>
          {#if !hidden && visibleCount > TAB_COUNT + 1}
            <span class="badge">{pos < TAB_COUNT ? 'Tab' : 'More'}</span>
          {/if}
          <button
            class="icon-btn"
            onclick={() => toggle(item)}
            disabled={item.required}
            title={item.required ? 'Settings is always shown' : hidden ? 'Show' : 'Hide'}
            aria-label={hidden ? `Show ${item.label}` : `Hide ${item.label}`}
          >
            <Icon name={hidden ? 'hidden' : 'visible'} size={20} />
          </button>
          <button class="icon-btn" onclick={() => move(i, -1)} disabled={i === 0} aria-label="Move {item.label} up">
            <Icon name="up" size={20} />
          </button>
          <button
            class="icon-btn"
            onclick={() => move(i, 1)}
            disabled={i === menu.length - 1}
            aria-label="Move {item.label} down"
          >
            <Icon name="chevronDown" size={20} />
          </button>
        </div>
      {/each}
    </div>
    <div class="row">
      <div class="label">Default menu</div>
      <button class="btn" onclick={resetMenu}><Icon name="undo" size={18} /> Reset</button>
    </div>
  </section>

  <section>
    <h2>Playback</h2>
    <div class="row">
      <div class="label">Tapping a song</div>
      <select bind:value={settings.tapAction}>
        {#each tapActions as a (a.id)}<option value={a.id}>{a.label}</option>{/each}
      </select>
    </div>
  </section>

  <section>
    <h2>Library</h2>
    <div class="row">
      <div class="label">
        Cover art cache
        <div class="hint">
          Order: embedded tags → folder images → Jellyfin → {(config?.web_art || []).join(', ') || 'no web lookups'}
        </div>
      </div>
      <button class="btn" onclick={clearArt}><Icon name="refresh" size={18} /> Clear</button>
    </div>
    <div class="row">
      <div class="label">
        Custom covers
        <div class="hint">
          {Object.keys(artState.overrides).length || 'No'} cover{Object.keys(artState.overrides).length === 1
            ? ''
            : 's'} picked by hand. Kept when the cache is cleared; undo one via its “Change cover…” menu.
        </div>
      </div>
    </div>
    <div class="row">
      <div class="label">Browse cache<div class="hint">Re-fetch albums, artists and folders</div></div>
      <button class="btn" onclick={reloadLibrary}><Icon name="refresh" size={18} /> Refresh</button>
    </div>
    {#if config?.local_scan}<LocalScan />{/if}
  </section>

  <section>
    <h2>About</h2>
    <div class="about">
      <div><span class="muted">Melody</span> {config?.version || '–'}</div>
      <div><span class="muted">Mopidy</span> {player.version || '–'}</div>
      <div>
        <span class="muted">Connection</span>
        {player.online ? 'connected' : 'offline'}
      </div>
      <div class="sources">
        {#each player.uriSchemes as s (s)}<span class="badge">{sourceName(s)}</span>{/each}
      </div>
    </div>
  </section>
</div>

<style>
  .narrow {
    max-width: 760px;
  }
  section {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 6px 18px;
    margin-bottom: 18px;
  }
  h2 {
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-3);
    margin: 14px 0 4px;
  }
  .row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 14px 0;
    border-top: 1px solid var(--border);
    flex-wrap: wrap;
  }
  h2 + .row {
    border-top: 0;
  }
  .label {
    font-weight: 600;
  }
  .hint {
    font-size: 13px;
    color: var(--text-3);
    font-weight: 400;
    margin-top: 2px;
  }
  .seg {
    display: flex;
    gap: 4px;
    padding: 4px;
    border-radius: 999px;
    background: var(--surface-2);
  }
  .seg button {
    padding: 7px 16px;
    border-radius: 999px;
    font-weight: 600;
    font-size: 14px;
    color: var(--text-2);
  }
  .seg button.active {
    background: var(--bg-elev);
    color: var(--text);
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
  }
  .swatches {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .swatch {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    color: #fff;
    transition: transform 0.15s var(--ease);
    position: relative;
    cursor: pointer;
  }
  .swatch:hover {
    transform: scale(1.1);
  }
  .swatch.active {
    box-shadow:
      0 0 0 2px var(--bg-elev),
      0 0 0 4px var(--text);
  }
  .custom {
    background: conic-gradient(red, yellow, lime, cyan, blue, magenta, red);
  }
  .custom input {
    position: absolute;
    inset: 0;
    opacity: 0;
    cursor: pointer;
  }
  select {
    height: 40px;
    padding: 0 12px;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--surface-2);
  }
  .menu-hint {
    margin: 0 0 8px;
  }
  .menu {
    display: flex;
    flex-direction: column;
    padding-bottom: 6px;
  }
  .menu-row {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 4px 0 4px 4px;
    border-top: 1px solid var(--border);
  }
  .menu-row > :global(svg) {
    color: var(--text-2);
  }
  .menu-label {
    flex: 1;
    font-weight: 600;
  }
  .menu-row.hidden .menu-label,
  .menu-row.hidden > :global(svg) {
    opacity: 0.45;
  }
  .about {
    display: grid;
    gap: 6px;
    padding: 8px 0 16px;
  }
  .sources {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 6px;
  }
</style>
