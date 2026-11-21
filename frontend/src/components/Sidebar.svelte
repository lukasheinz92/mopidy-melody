<script>
  import Icon from './Icon.svelte';
  import Logo from './Logo.svelte';
  import { route } from '../lib/router.svelte.js';
  import { navItems, isActive } from '../lib/nav.js';
  import { player } from '../lib/player.svelte.js';

  let { config } = $props();
  const items = $derived(navItems(config));
</script>

<nav class="sidebar">
  <a class="brand" href="#/">
    <Logo size={34} />
    <span>{config?.title || 'Melody'}</span>
  </a>
  <div class="items">
    {#each items as item (item.path)}
      <a class="item" class:active={isActive(item, route.path)} href={'#' + item.path}>
        <Icon name={item.icon} size={22} />
        <span>{item.label}</span>
        {#if item.path === '/queue' && player.tracklist.length}
          <span class="count">{player.tracklist.length}</span>
        {/if}
      </a>
    {/each}
  </div>
  {#if !player.online}
    <div class="offline"><Icon name="offline" size={18} /> Reconnecting…</div>
  {/if}
</nav>

<style>
  .sidebar {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 18px 12px;
    background: var(--bg-elev);
    border-right: 1px solid var(--border);
    overflow-y: auto;
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 10px 18px;
    font-size: 20px;
    font-weight: 800;
    letter-spacing: -0.02em;
  }
  .items {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .item {
    display: flex;
    align-items: center;
    gap: 14px;
    height: 44px;
    padding: 0 12px;
    border-radius: 10px;
    color: var(--text-2);
    font-weight: 600;
    transition:
      background 0.15s,
      color 0.15s;
  }
  .item:hover {
    background: var(--surface-hover);
    color: var(--text);
  }
  .item.active {
    background: var(--accent-soft);
    color: var(--accent-text);
  }
  .count {
    margin-left: auto;
    font-size: 12px;
    padding: 1px 8px;
    border-radius: 999px;
    background: var(--surface-2);
    color: var(--text-2);
  }
  .offline {
    margin-top: auto;
    display: flex;
    gap: 8px;
    align-items: center;
    padding: 10px 12px;
    border-radius: 10px;
    background: color-mix(in srgb, #ef4444 15%, transparent);
    color: #ef4444;
    font-size: 13px;
    font-weight: 600;
  }
</style>
