<script>
  // Pointer-driven slider (works for mouse + touch); emits while dragging.
  let {
    value = 0,
    max = 100,
    oninput,
    onchange,
    disabled = false,
    label = '',
    class: cls = '',
  } = $props();

  let el;
  let dragging = $state(false);
  let dragValue = $state(0);
  const shown = $derived(dragging ? dragValue : value);
  const pct = $derived(max > 0 ? Math.min(100, Math.max(0, (shown / max) * 100)) : 0);

  function valueAt(e) {
    const rect = el.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
    return ratio * max;
  }

  function down(e) {
    if (disabled || !max) return;
    el.setPointerCapture(e.pointerId);
    dragging = true;
    dragValue = valueAt(e);
    oninput?.(dragValue);
  }
  function move(e) {
    if (!dragging) return;
    dragValue = valueAt(e);
    oninput?.(dragValue);
  }
  function up() {
    if (!dragging) return;
    dragging = false;
    onchange?.(dragValue);
  }
  function key(e) {
    const step = max / 20;
    if (e.key === 'ArrowRight' || e.key === 'ArrowUp') onchange?.(Math.min(max, value + step));
    if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') onchange?.(Math.max(0, value - step));
  }
</script>

<div
  bind:this={el}
  class="slider {cls}"
  class:dragging
  class:disabled
  role="slider"
  tabindex={disabled ? -1 : 0}
  aria-label={label}
  aria-valuemin="0"
  aria-valuemax={max}
  aria-valuenow={Math.round(shown)}
  onpointerdown={down}
  onpointermove={move}
  onpointerup={up}
  onpointercancel={up}
  onkeydown={key}
>
  <div class="track"><div class="fill" style="width:{pct}%"></div></div>
  <div class="thumb" style="left:{pct}%"></div>
</div>

<style>
  .slider {
    position: relative;
    height: 20px;
    display: flex;
    align-items: center;
    cursor: pointer;
    touch-action: none;
    flex: 1;
    min-width: 60px;
    outline: none;
  }
  .disabled {
    cursor: default;
    opacity: 0.5;
  }
  .track {
    width: 100%;
    height: 4px;
    border-radius: 4px;
    background: color-mix(in srgb, var(--text) 18%, transparent);
    overflow: hidden;
  }
  .fill {
    height: 100%;
    background: var(--text);
    border-radius: 4px;
  }
  .slider:hover .fill,
  .dragging .fill,
  .slider:focus-visible .fill {
    background: var(--accent);
  }
  .thumb {
    position: absolute;
    top: 50%;
    width: 13px;
    height: 13px;
    border-radius: 50%;
    background: var(--text);
    transform: translate(-50%, -50%) scale(0);
    transition: transform 0.15s var(--ease);
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.4);
  }
  .slider:hover .thumb,
  .dragging .thumb,
  .slider:focus-visible .thumb {
    transform: translate(-50%, -50%) scale(1);
  }
  @media (hover: none) {
    .thumb {
      transform: translate(-50%, -50%) scale(1);
    }
  }
</style>
