<script>
  // Action sheet: bottom sheet on mobile, centered menu on desktop.
  import Cover from './Cover.svelte';
  import Icon from './Icon.svelte';
  import { ui, closeSheet } from '../lib/ui.svelte.js';
  import { fade, fly } from 'svelte/transition';

  function run(action) {
    closeSheet();
    action.run();
  }
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && ui.sheet && closeSheet()} />

{#if ui.sheet}
  <div
    class="backdrop"
    transition:fade={{ duration: 150 }}
    onclick={closeSheet}
    role="presentation"
  ></div>
  <div class="sheet" role="dialog" aria-modal="true" transition:fly={{ y: 40, duration: 220 }}>
    <div class="head">
      {#if ui.sheet.image}
        <div class="img"><Cover src={ui.sheet.image} eager /></div>
      {/if}
      <div class="titles">
        <div class="title ellipsis">{ui.sheet.title}</div>
        {#if ui.sheet.subtitle}<div class="subtitle ellipsis">{ui.sheet.subtitle}</div>{/if}
      </div>
    </div>
    <div class="actions">
      {#each ui.sheet.actions as action}
        <button class="action" class:danger={action.danger} onclick={() => run(action)}>
          <Icon name={action.icon} size={22} />
          <span>{action.label}</span>
        </button>
      {/each}
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 90;
    backdrop-filter: blur(2px);
  }
  .sheet {
    position: fixed;
    z-index: 91;
    left: 50%;
    top: 50%;
    translate: -50% -50%;
    width: min(380px, calc(100vw - 32px));
    max-height: 80vh;
    overflow: auto;
    background: var(--bg-elev);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 8px;
  }
  @media (max-width: 799px) {
    .sheet {
      top: auto;
      bottom: 0;
      left: 0;
      translate: none;
      width: 100%;
      max-height: 85vh;
      border-radius: 20px 20px 0 0;
      padding-bottom: calc(12px + var(--safe-bottom));
    }
  }
  .head {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 10px 14px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 6px;
  }
  .img {
    width: 52px;
  }
  .titles {
    min-width: 0;
  }
  .title {
    font-weight: 650;
  }
  .subtitle {
    color: var(--text-2);
    font-size: 13.5px;
    margin-top: 2px;
  }
  .action {
    display: flex;
    align-items: center;
    gap: 14px;
    width: 100%;
    padding: 12px;
    border-radius: var(--radius-sm);
    text-align: left;
    color: var(--text);
  }
  .action :global(svg) {
    color: var(--text-2);
  }
  .action:hover {
    background: var(--surface-hover);
  }
  .danger,
  .danger :global(svg) {
    color: #ef4444 !important;
  }
</style>
