<script>
  import Icon from './Icon.svelte';
  import { ui } from '../lib/ui.svelte.js';
  import { playlists, isEditablePlaylist } from '../lib/library.js';
  import { fade, scale } from 'svelte/transition';

  let value = $state('');
  let input = $state();

  $effect(() => {
    if (ui.dialog?.kind === 'prompt') {
      value = ui.dialog.value || '';
      queueMicrotask(() => input?.focus());
    }
  });

  const close = (v = null) => ui.dialog?.resolve(v);

  function submit(e) {
    e.preventDefault();
    if (value.trim()) close(value.trim());
  }
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && ui.dialog && close()} />

{#if ui.dialog}
  {@const d = ui.dialog}
  <div
    class="backdrop"
    transition:fade={{ duration: 150 }}
    onclick={() => close()}
    role="presentation"
  ></div>
  <div class="dialog" role="dialog" aria-modal="true" transition:scale={{ start: 0.95, duration: 180 }}>
    <h2>{d.title}</h2>
    {#if d.kind === 'prompt'}
      <form onsubmit={submit}>
        <div class="field"><input bind:this={input} bind:value placeholder={d.placeholder} /></div>
        <div class="buttons">
          <button type="button" class="btn" onclick={() => close()}>Cancel</button>
          <button type="submit" class="btn primary" disabled={!value.trim()}>
            {d.confirmLabel || 'Save'}
          </button>
        </div>
      </form>
    {:else if d.kind === 'confirm'}
      <p class="muted">{d.message}</p>
      <div class="buttons">
        <button class="btn" onclick={() => close(false)}>Cancel</button>
        <button class="btn primary" class:danger-bg={d.danger} onclick={() => close(true)}>
          {d.confirmLabel || 'OK'}
        </button>
      </div>
    {:else if d.kind === 'playlist'}
      <div class="list">
        <button class="item new" onclick={() => close('new')}>
          <span class="ic"><Icon name="add" /></span> New playlist…
        </button>
        {#await playlists()}
          <div class="spinner"></div>
        {:then list}
          {#each list.filter((p) => isEditablePlaylist(p.uri)) as pl (pl.uri)}
            <button class="item" onclick={() => close(pl)}>
              <span class="ic"><Icon name="playlist" /></span>
              <span class="ellipsis">{pl.name}</span>
            </button>
          {/each}
        {/await}
      </div>
      <div class="buttons"><button class="btn" onclick={() => close()}>Cancel</button></div>
    {/if}
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
    width: min(420px, calc(100vw - 32px));
    max-height: 80vh;
    display: flex;
    flex-direction: column;
    background: var(--bg-elev);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 22px;
  }
  h2 {
    margin: 0 0 16px;
    font-size: 19px;
  }
  .buttons {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 18px;
  }
  .btn:disabled {
    opacity: 0.5;
  }
  .danger-bg {
    background: #ef4444;
  }
  .list {
    overflow: auto;
    margin: 0 -10px;
  }
  .item {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 10px;
    border-radius: var(--radius-sm);
    text-align: left;
  }
  .item:hover {
    background: var(--surface-hover);
  }
  .ic {
    display: grid;
    place-items: center;
    width: 40px;
    height: 40px;
    border-radius: 8px;
    background: var(--surface-2);
    color: var(--text-2);
    flex-shrink: 0;
  }
  .new .ic {
    background: var(--accent-soft);
    color: var(--accent);
  }
</style>
