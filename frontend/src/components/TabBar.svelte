<script>
  import Icon from './Icon.svelte';
  import { route, navigate } from '../lib/router.svelte.js';
  import { tabItems, isActive } from '../lib/nav.js';
  import { openSheet } from '../lib/ui.svelte.js';

  let { config } = $props();
  const items = $derived(tabItems(config));
  const moreActive = $derived(items.more.some((i) => isActive(i, route.path)));

  function more() {
    openSheet({
      title: 'More',
      actions: items.more.map((i) => ({ icon: i.icon, label: i.label, run: () => navigate(i.path) })),
    });
  }
</script>

<nav class="tabbar">
  {#each items.tabs as item (item.path)}
    <a class="tab" class:active={isActive(item, route.path)} href={'#' + item.path}>
      <span class="pill"><Icon name={item.icon} size={24} /></span>
      <span class="label">{item.short || item.label}</span>
    </a>
  {/each}
  {#if items.more.length}
    <button class="tab" class:active={moreActive} onclick={more}>
      <span class="pill"><Icon name="more" size={24} /></span>
      <span class="label">More</span>
    </button>
  {/if}
</nav>

<style>
  .tabbar {
    display: flex;
    justify-content: space-around;
    height: calc(var(--tabbar-h) + var(--safe-bottom));
    padding-bottom: var(--safe-bottom);
    background: var(--bg-elev);
    border-top: 1px solid var(--border);
  }
  .tab {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    color: var(--text-3);
    font-size: 11px;
    font-weight: 600;
  }
  .pill {
    display: grid;
    place-items: center;
    width: 52px;
    height: 28px;
    border-radius: 999px;
    transition: background 0.2s;
  }
  .active {
    color: var(--text);
  }
  .active .pill {
    background: var(--accent-soft);
    color: var(--accent-text);
  }
</style>
