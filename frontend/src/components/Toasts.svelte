<script>
  import { toasts } from '../lib/toast.svelte.js';
  import { fly } from 'svelte/transition';
  import { flip } from 'svelte/animate';
</script>

<div class="toasts" aria-live="polite">
  {#each toasts as t (t.id)}
    <div
      class="toast"
      class:error={t.error}
      animate:flip={{ duration: 200 }}
      transition:fly={{ y: 20, duration: 200 }}
    >
      {t.message}
    </div>
  {/each}
</div>

<style>
  .toasts {
    position: fixed;
    left: 50%;
    translate: -50% 0;
    bottom: calc(var(--player-h) + 16px);
    z-index: 120;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    pointer-events: none;
  }
  @media (max-width: 799px) {
    .toasts {
      bottom: calc(var(--tabbar-h) + var(--mini-h) + var(--safe-bottom) + 12px);
    }
  }
  .toast {
    background: var(--text);
    color: var(--bg);
    padding: 10px 18px;
    border-radius: 999px;
    font-weight: 600;
    font-size: 14px;
    box-shadow: var(--shadow);
    max-width: calc(100vw - 32px);
  }
  .error {
    background: #ef4444;
    color: #fff;
  }
</style>
