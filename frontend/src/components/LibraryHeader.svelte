<script>
  // Mobile-only segmented switch between the library sections.
  import Icon from './Icon.svelte';
  import { route } from '../lib/router.svelte.js';
  import { navItems } from '../lib/nav.js';

  const LIBRARY = ['artists', 'albums', 'playlists'];
  const tabs = $derived(navItems().filter((i) => LIBRARY.includes(i.id)));
</script>

<div class="libhead">
  <div class="seg">
    {#each tabs as t (t.path)}
      <a href={'#' + t.path} class:active={route.path === t.path}>{t.label}</a>
    {/each}
  </div>
  <a class="icon-btn" href="#/settings" aria-label="Settings"><Icon name="settings" /></a>
</div>

<style>
  .libhead {
    display: none;
  }
  @media (max-width: 799px) {
    .libhead {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 16px;
    }
  }
  .seg {
    flex: 1;
    display: flex;
    gap: 4px;
    padding: 4px;
    border-radius: 999px;
    background: var(--surface-2);
  }
  .seg a {
    flex: 1;
    text-align: center;
    padding: 8px 0;
    border-radius: 999px;
    font-weight: 650;
    font-size: 14px;
    color: var(--text-2);
    transition:
      background 0.15s,
      color 0.15s;
  }
  .seg a.active {
    background: var(--bg-elev);
    color: var(--text);
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
  }
</style>
