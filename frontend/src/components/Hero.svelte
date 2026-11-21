<script>
  // Header for album / artist / playlist pages with a soft art-tinted backdrop.
  import Cover from './Cover.svelte';

  let { image, label, title, round = false, icon = 'album', children, actions } = $props();
</script>

<section class="hero">
  {#if image}
    <div class="tint" style:background-image="url('{image}')"></div>
  {/if}
  <div class="inner">
    <div class="art" class:round><Cover src={image} {round} {icon} eager /></div>
    <div class="info">
      {#if label}<div class="label">{label}</div>{/if}
      <h1>{title}</h1>
      <div class="meta">{@render children?.()}</div>
      {#if actions}<div class="actions">{@render actions()}</div>{/if}
    </div>
  </div>
</section>

<style>
  .hero {
    position: relative;
    margin: -24px calc(-1 * clamp(16px, 3vw, 40px)) 20px;
    padding: 40px clamp(16px, 3vw, 40px) 24px;
    overflow: hidden;
  }
  .tint {
    position: absolute;
    inset: -80px;
    background-size: cover;
    background-position: center;
    filter: blur(70px) saturate(1.5);
    opacity: 0.45;
  }
  .hero::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, transparent 30%, var(--bg));
  }
  .inner {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: flex-end;
    gap: clamp(18px, 3vw, 32px);
  }
  .art {
    width: clamp(160px, 22vw, 240px);
    flex-shrink: 0;
    filter: drop-shadow(0 16px 40px rgba(0, 0, 0, 0.4));
  }
  .info {
    min-width: 0;
    flex: 1;
  }
  .label {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-2);
  }
  h1 {
    margin: 6px 0 10px;
    font-size: clamp(26px, 4.4vw, 56px);
    font-weight: 850;
    letter-spacing: -0.03em;
    line-height: 1.05;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .meta {
    color: var(--text-2);
    font-size: 14.5px;
    font-weight: 500;
  }
  .meta :global(a) {
    color: var(--text);
    font-weight: 650;
  }
  .meta :global(a:hover) {
    text-decoration: underline;
  }
  .actions {
    display: flex;
    gap: 10px;
    margin-top: 20px;
    flex-wrap: wrap;
    align-items: center;
  }
  @media (max-width: 799px) {
    .hero {
      margin-top: -16px;
      padding-top: 24px;
    }
    .inner {
      flex-direction: column;
      align-items: center;
      text-align: center;
    }
    .art {
      width: min(62vw, 260px);
    }
    .actions {
      justify-content: center;
    }
  }
</style>
