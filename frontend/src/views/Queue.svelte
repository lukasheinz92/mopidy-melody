<script>
  // Queue with pointer-based drag & drop (mouse + touch) via the handle.
  import Cover from '../components/Cover.svelte';
  import Icon from '../components/Icon.svelte';
  import { player, controls } from '../lib/player.svelte.js';
  import { tracklist, createPlaylist } from '../lib/library.js';
  import { trackArt } from '../lib/art.svelte.js';
  import { duration, trackTitle, trackArtist, longDuration, plural } from '../lib/format.js';
  import { openSheet, prompt, confirm } from '../lib/ui.svelte.js';
  import { trackSheet } from '../lib/actions.js';
  import { toast, toastError } from '../lib/toast.svelte.js';

  let { panel = false } = $props();

  const ROW = 60;

  let order = $state(null); // optimistic order while a move is in flight
  const items = $derived(order ?? player.tracklist);
  const currentIndex = $derived(items.findIndex((t) => t.tlid === player.tlTrack?.tlid));
  const total = $derived(items.reduce((s, t) => s + (t.track.length || 0), 0));

  $effect(() => {
    player.tracklist;
    order = null;
  });

  // ---- drag & drop
  let drag = $state(null); // { from, to, offset }
  let scroller = null;
  let startY = 0;
  let startScroll = 0;
  let pointerY = 0;
  let raf = 0;

  function findScroller(el) {
    while (el && el !== document.body) {
      const s = getComputedStyle(el).overflowY;
      if ((s === 'auto' || s === 'scroll') && el.scrollHeight > el.clientHeight) return el;
      el = el.parentElement;
    }
    return document.scrollingElement;
  }

  function dragStart(e, index) {
    e.preventDefault();
    e.currentTarget.setPointerCapture(e.pointerId);
    scroller = findScroller(e.currentTarget);
    startY = pointerY = e.clientY;
    startScroll = scroller.scrollTop;
    drag = { from: index, to: index, offset: 0 };
    raf = requestAnimationFrame(autoScroll);
  }

  function update() {
    if (!drag) return;
    const offset = pointerY - startY + (scroller.scrollTop - startScroll);
    const to = Math.max(0, Math.min(items.length - 1, drag.from + Math.round(offset / ROW)));
    drag = { ...drag, offset, to };
  }

  function dragMove(e) {
    if (!drag) return;
    pointerY = e.clientY;
    update();
  }

  function autoScroll() {
    if (!drag) return;
    const rect = scroller.getBoundingClientRect?.() ?? { top: 0, bottom: innerHeight };
    const top = Math.max(rect.top, 0) + 60;
    const bottom = Math.min(rect.bottom, innerHeight) - 60;
    if (pointerY < top) scroller.scrollTop -= Math.ceil((top - pointerY) / 6);
    else if (pointerY > bottom) scroller.scrollTop += Math.ceil((pointerY - bottom) / 6);
    update();
    raf = requestAnimationFrame(autoScroll);
  }

  async function dragEnd() {
    if (!drag) return;
    cancelAnimationFrame(raf);
    const { from, to } = drag;
    drag = null;
    if (from === to) return;
    const next = [...items];
    next.splice(to, 0, next.splice(from, 1)[0]);
    order = next;
    try {
      await tracklist.move(from, from + 1, to);
    } catch (e) {
      order = null;
      toastError(e, 'Could not move');
    }
  }

  function shift(i) {
    if (!drag) return 0;
    if (i === drag.from) return drag.offset;
    if (drag.from < drag.to && i > drag.from && i <= drag.to) return -ROW;
    if (drag.from > drag.to && i < drag.from && i >= drag.to) return ROW;
    return 0;
  }

  // ---- actions
  async function save() {
    if (!items.length) return;
    const name = await prompt({ title: 'Save queue as playlist', placeholder: 'Playlist name' });
    if (!name) return;
    try {
      await createPlaylist(name, items.map((t) => t.track));
      toast(`Saved “${name}”`);
    } catch (e) {
      toastError(e, 'Could not save playlist');
    }
  }

  async function clear() {
    const ok = await confirm({
      title: 'Clear queue?',
      message: `Remove all ${plural(items.length, 'track')} from the queue.`,
      confirmLabel: 'Clear',
      danger: true,
    });
    if (ok) tracklist.clear().catch((e) => toastError(e));
  }

  function more(tl) {
    openSheet(
      trackSheet(tl.track, [
        { icon: 'delete', label: 'Remove from queue', danger: true, run: () => tracklist.remove([tl.tlid]) },
      ])
    );
  }

  function scrollToCurrent(node) {
    // Bring the playing track into view when the queue opens.
    queueMicrotask(() => node.querySelector('.current')?.scrollIntoView({ block: 'center' }));
  }
</script>

<div class:page={!panel} class:panel>
  <div class="head">
    <div>
      <h1>Queue</h1>
      {#if items.length}
        <div class="muted small">{plural(items.length, 'track')} · {longDuration(total)}</div>
      {/if}
    </div>
    <div class="tools">
      <button class="icon-btn" class:active={player.random} title="Shuffle playback" aria-label="Shuffle playback"
        onclick={() => controls.setRandom(!player.random)}><Icon name="shuffle" size={20} /></button>
      <button class="icon-btn" class:active={player.repeat} title="Repeat" aria-label="Repeat"
        onclick={() => controls.cycleRepeat()}><Icon name={player.single && player.repeat ? 'repeatOne' : 'repeat'} size={20} /></button>
      <button class="icon-btn" class:active={player.consume} title="Consume (remove played tracks)" aria-label="Consume"
        onclick={() => controls.setConsume(!player.consume)}><Icon name="consume" size={20} /></button>
      <button class="icon-btn" title="Save as playlist" aria-label="Save as playlist" disabled={!items.length} onclick={save}>
        <Icon name="save" size={20} />
      </button>
      <button class="icon-btn" title="Clear queue" aria-label="Clear queue" disabled={!items.length} onclick={clear}>
        <Icon name="clearAll" size={20} />
      </button>
    </div>
  </div>

  {#if items.length}
    <div class="list" use:scrollToCurrent class:dragging={!!drag} style:height="{items.length * ROW}px">
      {#each items as tl, i (tl.tlid)}
        <div
          class="row"
          class:current={i === currentIndex}
          class:played={currentIndex >= 0 && i < currentIndex}
          class:lifted={drag?.from === i}
          style:top="{i * ROW}px"
          style:transform="translateY({shift(i)}px)"
        >
          <button
            class="handle"
            aria-label="Drag to reorder"
            onpointerdown={(e) => dragStart(e, i)}
            onpointermove={dragMove}
            onpointerup={dragEnd}
            onpointercancel={dragEnd}
          >
            <Icon name="drag" size={20} />
          </button>
          <button class="main" onclick={() => controls.play(tl.tlid)}>
            <div class="thumb">
              <Cover src={trackArt(tl.track, 96)} icon="note" />
              {#if i === currentIndex}
                <span class="playing"><Icon name={player.state === 'playing' ? 'volume' : 'pause'} size={18} /></span>
              {/if}
            </div>
            <div class="meta">
              <div class="name ellipsis">{trackTitle(tl.track)}</div>
              <div class="sub ellipsis">{trackArtist(tl.track)}</div>
            </div>
            <span class="dur">{duration(tl.track.length)}</span>
          </button>
          <button class="icon-btn" aria-label="More" onclick={() => more(tl)}><Icon name="more" size={20} /></button>
          <button class="icon-btn remove" aria-label="Remove" onclick={() => tracklist.remove([tl.tlid])}>
            <Icon name="close" size={18} />
          </button>
        </div>
      {/each}
    </div>
  {:else}
    <div class="empty">
      <Icon name="queue" size={48} />
      <div>Your queue is empty</div>
      <a class="btn" href="#/browse">Browse music</a>
    </div>
  {/if}
</div>

<style>
  .panel {
    padding: 18px 12px 24px;
  }
  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 14px;
    flex-wrap: wrap;
  }
  .panel .head {
    padding: 0 4px;
  }
  h1 {
    margin: 0;
    font-size: clamp(24px, 3vw, 32px);
    font-weight: 750;
    letter-spacing: -0.02em;
  }
  .panel h1 {
    font-size: 20px;
  }
  .small {
    font-size: 13px;
    margin-top: 2px;
  }
  .tools {
    display: flex;
    gap: 2px;
  }
  .tools .icon-btn:disabled {
    opacity: 0.35;
  }
  .list {
    position: relative;
  }
  .row {
    position: absolute;
    left: 0;
    right: 0;
    height: 60px;
    display: flex;
    align-items: center;
    gap: 4px;
    padding-right: 4px;
    border-radius: var(--radius-sm);
    background: var(--bg);
    transition: transform 0.18s var(--ease);
  }
  .panel .row {
    background: var(--bg-elev);
  }
  .row:hover {
    background: color-mix(in srgb, var(--bg) 94%, var(--text));
  }
  .row.lifted {
    transition: none;
    z-index: 5;
    background: var(--surface-2);
    box-shadow: var(--shadow);
  }
  .dragging .row {
    user-select: none;
  }
  .handle {
    display: grid;
    place-items: center;
    width: 36px;
    height: 100%;
    color: var(--text-3);
    cursor: grab;
    touch-action: none;
    flex-shrink: 0;
  }
  .lifted .handle {
    cursor: grabbing;
  }
  .main {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 12px;
    height: 100%;
    text-align: left;
  }
  .thumb {
    position: relative;
    width: 44px;
    flex-shrink: 0;
  }
  .thumb :global(.cover) {
    border-radius: 6px;
  }
  .playing {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    background: rgba(0, 0, 0, 0.5);
    color: #fff;
    border-radius: 6px;
  }
  .meta {
    flex: 1;
    min-width: 0;
  }
  .name {
    font-weight: 550;
  }
  .sub {
    font-size: 13px;
    color: var(--text-2);
    margin-top: 2px;
  }
  .current .name {
    color: var(--accent-text);
  }
  .played {
    opacity: 0.55;
  }
  .dur {
    font-size: 13px;
    color: var(--text-3);
    font-variant-numeric: tabular-nums;
    padding: 0 4px;
  }
  .remove {
    opacity: 0;
  }
  .row:hover .remove {
    opacity: 1;
  }
  .panel .dur,
  .panel .remove {
    display: none;
  }
  @media (hover: none) {
    .remove {
      display: none;
    }
  }
  @media (max-width: 799px) {
    .dur {
      display: none;
    }
  }
</style>
