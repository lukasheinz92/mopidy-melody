<script>
  // Pick a cover by hand: web search results, a pasted URL or an upload.
  // The choice is stored on the server and wins over every automatic source.
  import Cover from './Cover.svelte';
  import Icon from './Icon.svelte';
  import { ui } from '../lib/ui.svelte.js';
  import { getArtCandidates, setArtOverride, removeArtOverride } from '../lib/api.js';
  import { artUrl, artState, applyArtOverrides } from '../lib/art.svelte.js';
  import { toast, toastError } from '../lib/toast.svelte.js';
  import { fade, scale } from 'svelte/transition';

  const TABS = [
    { id: 'search', icon: 'search', label: 'Search' },
    { id: 'url', icon: 'link', label: 'URL' },
    { id: 'upload', icon: 'upload', label: 'Upload' },
  ];

  let tab = $state('search');
  let query = $state('');
  let url = $state('');
  let results = $state(null); // null = loading
  let saving = $state(false);
  let searchId = 0;

  const target = $derived(ui.coverPicker);
  const overridden = $derived(target && artState.overrides[target.uri]);

  $effect(() => {
    if (!target) return;
    tab = 'search';
    url = '';
    query = target.query || '';
    search();
  });

  async function search(e) {
    e?.preventDefault();
    const id = ++searchId;
    results = null;
    try {
      const found = await getArtCandidates(target.uri, target.kind, query.trim());
      if (id === searchId) results = found;
    } catch (err) {
      if (id === searchId) results = [];
      toastError(err, 'Search failed');
    }
  }

  const close = () => (ui.coverPicker = null);

  async function save(image) {
    if (saving) return;
    saving = true;
    try {
      applyArtOverrides(await setArtOverride(target.uri, image));
      toast('Cover changed');
      close();
    } catch (err) {
      toastError(err, 'Could not change the cover');
    } finally {
      saving = false;
    }
  }

  async function restore() {
    saving = true;
    try {
      applyArtOverrides(await removeArtOverride(target.uri));
      toast('Automatic cover restored');
      close();
    } catch (err) {
      toastError(err);
    } finally {
      saving = false;
    }
  }

  function upload(e) {
    const file = e.currentTarget.files?.[0];
    if (file) save(file);
  }
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && target && close()} />

{#if target}
  <div class="backdrop" transition:fade={{ duration: 150 }} onclick={close} role="presentation"></div>
  <div class="dialog" role="dialog" aria-modal="true" transition:scale={{ start: 0.95, duration: 180 }}>
    <div class="head">
      <div class="current" class:round={target.kind === 'artist'}>
        <Cover
          src={artUrl(target.uri, { kind: target.kind, size: 256 })}
          round={target.kind === 'artist'}
          icon={target.kind === 'artist' ? 'artist' : 'album'}
          eager
        />
      </div>
      <div class="titles">
        <h2 class="ellipsis">{target.kind === 'artist' ? 'Change picture' : 'Change cover'}</h2>
        <div class="muted ellipsis">{target.title || target.uri}</div>
        {#if overridden}
          <button class="btn small" onclick={restore} disabled={saving}>
            <Icon name="undo" size={16} /> Restore automatic
          </button>
        {/if}
      </div>
      <button class="icon-btn" onclick={close} aria-label="Close"><Icon name="close" /></button>
    </div>

    <div class="seg">
      {#each TABS as t (t.id)}
        <button class:active={tab === t.id} onclick={() => (tab = t.id)}>
          <Icon name={t.icon} size={18} />
          {t.label}
        </button>
      {/each}
    </div>

    <div class="body">
      {#if tab === 'search'}
        <form class="field" onsubmit={search}>
          <Icon name="search" size={20} />
          <input bind:value={query} placeholder="Artist and album…" enterkeyhint="search" type="search" />
        </form>
        {#if results === null}
          <div class="spinner"></div>
        {:else if !results.length}
          <div class="empty-msg muted">No images found. Try another search, a URL or an upload.</div>
        {:else}
          <div class="results">
            {#each results as c (c.url)}
              <button class="result" onclick={() => save(c.url)} disabled={saving} title="{c.title} {c.subtitle}">
                <Cover src={c.thumb} round={target.kind === 'artist'} />
                <span class="r-title ellipsis">{c.title || 'Current source'}</span>
                <span class="r-sub ellipsis">{[c.subtitle, c.source].filter(Boolean).join(' · ')}</span>
              </button>
            {/each}
          </div>
        {/if}
      {:else if tab === 'url'}
        <form
          class="url"
          onsubmit={(e) => {
            e.preventDefault();
            if (url.trim()) save(url.trim());
          }}
        >
          <div class="field">
            <Icon name="link" size={20} />
            <input bind:value={url} placeholder="https://…/cover.jpg" type="url" inputmode="url" />
          </div>
          {#if url.trim()}
            <div class="preview"><Cover src={url.trim()} round={target.kind === 'artist'} /></div>
          {/if}
          <div class="buttons">
            <button type="submit" class="btn primary" disabled={!url.trim() || saving}>Use this image</button>
          </div>
        </form>
      {:else}
        <label class="drop">
          <Icon name="image" size={40} />
          <span>Choose an image (JPEG, PNG, WebP)</span>
          <input type="file" accept="image/*" onchange={upload} disabled={saving} />
        </label>
      {/if}
      {#if saving}<div class="saving muted"><span class="spinner small"></span> Saving…</div>{/if}
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
    z-index: 100;
  }
  .dialog {
    position: fixed;
    z-index: 101;
    left: 50%;
    top: 50%;
    translate: -50% -50%;
    width: min(640px, calc(100vw - 24px));
    height: min(720px, calc(100dvh - 48px));
    display: flex;
    flex-direction: column;
    gap: 14px;
    background: var(--bg-elev);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 18px;
  }
  .head {
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .current {
    width: 72px;
    flex-shrink: 0;
  }
  .titles {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }
  h2 {
    margin: 0;
    font-size: 19px;
    max-width: 100%;
  }
  .titles .muted {
    max-width: 100%;
    font-size: 13.5px;
  }
  .small {
    height: 32px;
    padding: 0 12px;
    font-size: 13px;
    margin-top: 4px;
  }
  .seg {
    display: flex;
    gap: 4px;
    padding: 4px;
    border-radius: 999px;
    background: var(--surface-2);
  }
  .seg button {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 7px 10px;
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
  .body {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .results {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 14px;
  }
  .result {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 6px;
    border-radius: var(--radius-sm);
    text-align: left;
    min-width: 0;
  }
  .result:hover {
    background: var(--surface-hover);
  }
  .r-title {
    font-weight: 600;
    font-size: 13.5px;
    margin-top: 4px;
  }
  .r-sub {
    color: var(--text-3);
    font-size: 12px;
  }
  .empty-msg {
    padding: 30px 10px;
    text-align: center;
  }
  .url {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .preview {
    width: 200px;
    align-self: center;
  }
  .buttons {
    display: flex;
    justify-content: flex-end;
  }
  .btn:disabled,
  .result:disabled {
    opacity: 0.5;
  }
  .drop {
    flex: 1;
    min-height: 200px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    border: 2px dashed var(--border);
    border-radius: var(--radius);
    color: var(--text-2);
    cursor: pointer;
    position: relative;
  }
  .drop:hover {
    border-color: var(--accent);
    color: var(--text);
  }
  .drop input {
    position: absolute;
    inset: 0;
    opacity: 0;
    cursor: pointer;
  }
  .spinner.small {
    width: 18px;
    height: 18px;
    border-width: 2px;
    margin: 0;
  }
  .saving {
    display: flex;
    align-items: center;
    gap: 8px;
    justify-content: center;
  }
</style>
