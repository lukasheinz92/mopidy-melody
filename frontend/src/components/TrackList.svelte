<script>
  import Cover from './Cover.svelte';
  import Icon from './Icon.svelte';
  import { duration, trackTitle, trackArtist } from '../lib/format.js';
  import { trackArt } from '../lib/art.svelte.js';
  import { tapTrack, playNow, playNext, addToQueue } from '../lib/library.js';
  import { trackSheet } from '../lib/actions.js';
  import { openSheet } from '../lib/ui.svelte.js';
  import { player } from '../lib/player.svelte.js';

  let {
    tracks = [],
    numbered = false, // show track numbers (album view)
    covers = true,
    album = true,
    discs = false,
    extraActions, // (track, index) => [{ icon, label, run }]
    ontap, // (track, index) => Promise; default: the "Tapping a song" setting
    quick = false, // inline play now / play next / add to queue buttons
  } = $props();

  // Rows whose action is still running (remote backends can take seconds).
  let busy = $state({});

  const currentUri = $derived(player.tlTrack?.track?.uri);
  const multiDisc = $derived(discs && new Set(tracks.map((t) => t.disc_no || 1)).size > 1);

  async function act(key, fn) {
    if (busy[key]) return;
    busy[key] = true;
    try {
      await fn();
    } finally {
      delete busy[key];
    }
  }

  function tap(track, i) {
    act(i, () => (ontap ? ontap(track, i) : tapTrack(track.uri)));
  }

  function quickAction(e, i, fn) {
    e.stopPropagation();
    act(i, fn);
  }

  function more(e, track, i) {
    e.preventDefault();
    e.stopPropagation();
    openSheet(trackSheet(track, extraActions?.(track, i) || []));
  }
</script>

<div class="tracks">
  {#each tracks as track, i (track.uri + ':' + i)}
    {#if multiDisc && (i === 0 || (tracks[i - 1].disc_no || 1) !== (track.disc_no || 1))}
      <div class="disc"><Icon name="album" size={16} /> Disc {track.disc_no || 1}</div>
    {/if}
    <div
      class="row"
      class:current={track.uri === currentUri}
      class:with-album={album}
      class:quick
      class:busy={busy[i]}
      role="button"
      tabindex="0"
      onclick={() => tap(track, i)}
      onkeydown={(e) => e.target === e.currentTarget && e.key === 'Enter' && tap(track, i)}
      oncontextmenu={(e) => more(e, track, i)}
    >
      {#if numbered}
        <div class="num">
          {#if track.uri === currentUri && player.state === 'playing'}
            <span class="eq"><i></i><i></i><i></i></span>
          {:else}
            {track.track_no || i + 1}
          {/if}
        </div>
      {:else if covers}
        <div class="thumb"><Cover src={trackArt(track, 96)} icon="note" /></div>
      {:else}
        <div></div>
      {/if}
      <div class="meta">
        <div class="name ellipsis">{trackTitle(track)}</div>
        <div class="sub ellipsis">{trackArtist(track)}</div>
      </div>
      {#if album}
        <div class="album ellipsis">{track.album?.name || ''}</div>
      {/if}
      {#if quick}
        <div class="quick-btns">
          {#if busy[i]}
            <span class="mini-spin" aria-label="Working…"></span>
          {:else}
            <button
              class="icon-btn"
              title="Play now"
              aria-label="Play now"
              onclick={(e) => quickAction(e, i, () => playNow([track.uri]))}
            ><Icon name="play" size={20} /></button>
            <button
              class="icon-btn"
              title="Play next"
              aria-label="Play next"
              onclick={(e) => quickAction(e, i, () => playNext([track.uri]))}
            ><Icon name="playNext" size={20} /></button>
            <button
              class="icon-btn"
              title="Add to queue"
              aria-label="Add to queue"
              onclick={(e) => quickAction(e, i, () => addToQueue([track.uri]))}
            ><Icon name="queue" size={20} /></button>
          {/if}
        </div>
      {/if}
      <div class="dur">{duration(track.length)}</div>
      <button class="icon-btn more" aria-label="More" onclick={(e) => more(e, track, i)}>
        <Icon name="more" size={20} />
      </button>
    </div>
  {/each}
</div>

<style>
  .tracks {
    display: flex;
    flex-direction: column;
  }
  .disc {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--text-2);
    font-weight: 600;
    font-size: 13px;
    padding: 18px 12px 6px;
  }
  .row {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr) 56px 40px;
    align-items: center;
    gap: 14px;
    padding: 6px 4px 6px 12px;
    border-radius: var(--radius-sm);
    cursor: pointer;
    min-height: 56px;
    transition: background 0.12s;
  }
  .row.with-album {
    grid-template-columns: auto minmax(0, 1fr) minmax(0, 0.7fr) 56px 40px;
  }
  .row.quick {
    grid-template-columns: auto minmax(0, 1fr) auto 56px 40px;
  }
  .row.quick.with-album {
    grid-template-columns: auto minmax(0, 1fr) minmax(0, 0.7fr) auto 56px 40px;
  }
  .row.busy {
    cursor: progress;
  }
  .quick-btns {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    min-width: 120px;
  }
  .quick-btns .icon-btn {
    color: var(--text-2);
  }
  .mini-spin {
    width: 18px;
    height: 18px;
    margin-right: 11px;
    border-radius: 50%;
    border: 2px solid var(--surface);
    border-top-color: var(--accent);
    animation: spin 0.8s linear infinite;
  }
  .row:hover {
    background: var(--surface-hover);
  }
  .row.current .name {
    color: var(--accent-text);
  }
  .num {
    width: 26px;
    text-align: right;
    color: var(--text-3);
    font-variant-numeric: tabular-nums;
    font-size: 14px;
  }
  .thumb {
    width: 44px;
  }
  .thumb :global(.cover) {
    border-radius: 6px;
  }
  .meta {
    min-width: 0;
  }
  .name {
    font-weight: 550;
  }
  .sub,
  .album {
    color: var(--text-2);
    font-size: 13.5px;
    margin-top: 2px;
  }
  .dur {
    color: var(--text-3);
    font-size: 13.5px;
    text-align: right;
    font-variant-numeric: tabular-nums;
  }
  .more {
    opacity: 0.7;
  }
  @media (max-width: 799px) {
    .row,
    .row.with-album {
      grid-template-columns: auto minmax(0, 1fr) 36px;
      gap: 12px;
      padding-left: 6px;
    }
    .row.quick,
    .row.quick.with-album {
      grid-template-columns: auto minmax(0, 1fr) auto 36px;
      gap: 8px;
    }
    .quick-btns {
      min-width: 108px;
    }
    .quick-btns .icon-btn {
      width: 36px;
      height: 36px;
    }
    .album,
    .dur {
      display: none;
    }
  }
  .eq {
    display: inline-flex;
    gap: 2px;
    align-items: flex-end;
    height: 14px;
  }
  .eq i {
    width: 3px;
    background: var(--accent);
    border-radius: 1px;
    animation: eq 0.9s ease-in-out infinite;
  }
  .eq i:nth-child(2) {
    animation-delay: -0.3s;
  }
  .eq i:nth-child(3) {
    animation-delay: -0.6s;
  }
  @keyframes eq {
    0%,
    100% {
      height: 4px;
    }
    50% {
      height: 14px;
    }
  }
</style>
