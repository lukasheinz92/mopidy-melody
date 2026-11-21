<script>
  // Full-screen player with the cover art as a blurred backdrop.
  import Cover from './Cover.svelte';
  import Icon from './Icon.svelte';
  import Slider from './Slider.svelte';
  import { player, controls, position, currentTrack } from '../lib/player.svelte.js';
  import { trackArt } from '../lib/art.svelte.js';
  import { duration, artistNames, trackTitle, trackArtist, sourceName, year } from '../lib/format.js';
  import { ui, openSheet } from '../lib/ui.svelte.js';
  import { navigate } from '../lib/router.svelte.js';
  import { trackSheet } from '../lib/actions.js';
  import { fly } from 'svelte/transition';

  let { config } = $props();

  const track = $derived(currentTrack());
  const art = $derived(trackArt(track, 1024));
  const upNext = $derived.by(() => {
    const i = player.tracklist.findIndex((t) => t.tlid === player.tlTrack?.tlid);
    return i >= 0 ? player.tracklist.slice(i + 1, i + 4) : [];
  });

  function close() {
    ui.nowPlaying = false;
  }

  function go(path, params) {
    close();
    navigate(path, params);
  }

  // Swipe down to close (mobile).
  let startY = null;
  let dragY = $state(0);
  function touchStart(e) {
    const el = e.target.closest('.slider, button, a');
    startY = el ? null : e.touches[0].clientY;
  }
  function touchMove(e) {
    if (startY == null) return;
    dragY = Math.max(0, e.touches[0].clientY - startY);
  }
  function touchEnd() {
    if (dragY > 120) close();
    dragY = 0;
    startY = null;
  }
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && close()} />

<div
  class="np"
  transition:fly={{ y: 600, duration: 320, opacity: 1 }}
  style:transform={dragY ? `translateY(${dragY}px)` : null}
  ontouchstart={touchStart}
  ontouchmove={touchMove}
  ontouchend={touchEnd}
  role="dialog"
  aria-modal="true"
  aria-label="Now playing"
  tabindex="-1"
>
  {#if art}
    <div class="backdrop" style:background-image="url('{art}')"></div>
  {/if}
  <div class="shade"></div>

  <header>
    <button class="icon-btn" onclick={close} aria-label="Close"><Icon name="chevronDown" size={30} /></button>
    <div class="source">
      {#if track}<span class="muted">Playing from</span> {sourceName(track.uri)}{/if}
    </div>
    {#if track}
      <button class="icon-btn" aria-label="More" onclick={() => openSheet(trackSheet(track))}>
        <Icon name="more" />
      </button>
    {:else}
      <span style="width:40px"></span>
    {/if}
  </header>

  {#if track}
    <div class="body">
      <div class="art"><Cover src={art} icon="note" eager /></div>

      <div class="panel">
        <div class="titles">
          <h1>{player.streamTitle || trackTitle(track)}</h1>
          <div class="artist">
            {#if player.streamTitle}
              {track.name}
            {:else}
              {#if !track.artists?.length}{trackArtist(track)}{/if}
              {#each track.artists || [] as a, i}
                {#if i},&nbsp;{/if}
                {#if a.uri}
                  <button class="link" onclick={() => go('/artist', { uri: a.uri, name: a.name })}>{a.name}</button>
                {:else}{a.name}{/if}
              {/each}
            {/if}
          </div>
          {#if track.album?.name}
            <div class="album">
              {#if track.album.uri}
                <button class="link" onclick={() => go('/album', { uri: track.album.uri })}>{track.album.name}</button>
              {:else}{track.album.name}{/if}
              {#if year(track.date || track.album.date)}<span> · {year(track.date || track.album.date)}</span>{/if}
            </div>
          {/if}
        </div>

        <div class="seek">
          <Slider
            value={position()}
            max={track.length || 0}
            disabled={!track.length}
            onchange={(v) => controls.seek(v)}
            label="Seek"
          />
          <div class="times">
            <span>{duration(position())}</span>
            <span>{track.length ? duration(track.length) : 'LIVE'}</span>
          </div>
        </div>

        <div class="controls">
          <button
            class="icon-btn"
            class:active={player.random}
            onclick={() => controls.setRandom(!player.random)}
            aria-label="Shuffle"><Icon name="shuffle" /></button
          >
          <button class="icon-btn big" onclick={() => controls.previous()} aria-label="Previous">
            <Icon name="previous" size={36} />
          </button>
          <button class="play" onclick={() => controls.toggle()} aria-label="Play/Pause">
            <Icon name={player.state === 'playing' ? 'pause' : 'play'} size={38} />
          </button>
          <button
            class="icon-btn"
            onclick={() => controls.stop()}
            disabled={player.state === 'stopped'}
            aria-label="Stop"><Icon name="stop" /></button
          >
          <button class="icon-btn big" onclick={() => controls.next()} aria-label="Next">
            <Icon name="next" size={36} />
          </button>
          <button
            class="icon-btn"
            class:active={player.repeat}
            onclick={() => controls.cycleRepeat()}
            aria-label="Repeat"
          >
            <Icon name={player.single && player.repeat ? 'repeatOne' : 'repeat'} />
          </button>
        </div>

        <div class="volume">
          <button class="icon-btn" onclick={() => controls.toggleMute()} aria-label="Mute">
            <Icon name={player.mute || player.volume === 0 ? 'volumeOff' : 'volume'} size={20} />
          </button>
          <Slider
            value={player.volume ?? 0}
            max={100}
            disabled={player.volume == null}
            oninput={(v) => controls.setVolume(v)}
            onchange={(v) => controls.setVolume(v)}
            label="Volume"
          />
        </div>

        <div class="extras">
          <button
            class="icon-btn"
            class:active={player.consume}
            onclick={() => controls.setConsume(!player.consume)}
            title="Consume mode: remove tracks after playing"
            aria-label="Consume"><Icon name="consume" size={20} /></button
          >
          {#if config?.snapcast}
            <button class="icon-btn" onclick={() => go('/rooms')} aria-label="Rooms"><Icon name="speaker" size={20} /></button>
          {/if}
          <button class="icon-btn" onclick={() => go('/queue')} aria-label="Queue"><Icon name="queue" size={20} /></button>
        </div>

        {#if upNext.length}
          <div class="upnext">
            <div class="label">Up next</div>
            {#each upNext as tl (tl.tlid)}
              <button class="next-row" onclick={() => controls.play(tl.tlid)}>
                <div class="thumb"><Cover src={trackArt(tl.track, 96)} icon="note" /></div>
                <div class="ellipsis">
                  <div class="ellipsis">{trackTitle(tl.track)}</div>
                  <div class="muted ellipsis small">{trackArtist(tl.track)}</div>
                </div>
              </button>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  {:else}
    <div class="empty">
      <Icon name="note" size={48} />
      <div>Nothing is playing</div>
    </div>
  {/if}
</div>

<style>
  .np {
    position: fixed;
    inset: 0;
    z-index: 80;
    display: flex;
    flex-direction: column;
    background: var(--bg);
    overflow: hidden;
    transition: transform 0.05s;
    --text: #fff;
    --text-2: rgba(255, 255, 255, 0.72);
    --text-3: rgba(255, 255, 255, 0.5);
    --surface-hover: rgba(255, 255, 255, 0.1);
    color: #fff;
  }
  .backdrop {
    position: absolute;
    inset: -60px;
    background-size: cover;
    background-position: center;
    filter: blur(60px) saturate(1.4);
    opacity: 0.85;
    transform: scale(1.1);
  }
  .shade {
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, rgba(0, 0, 0, 0.35), rgba(0, 0, 0, 0.7));
  }
  header,
  .body,
  .empty {
    position: relative;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: max(10px, env(safe-area-inset-top)) 12px 4px;
  }
  .source {
    font-size: 12.5px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    text-align: center;
  }
  .body {
    flex: 1;
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(320px, 440px);
    align-items: center;
    gap: clamp(24px, 5vw, 80px);
    padding: 12px clamp(20px, 6vw, 96px) 40px;
    min-height: 0;
  }
  .art {
    width: min(100%, 62vh);
    justify-self: end;
    filter: drop-shadow(0 24px 60px rgba(0, 0, 0, 0.55));
  }
  .art :global(.cover) {
    border-radius: 14px;
  }
  .panel {
    display: flex;
    flex-direction: column;
    gap: 22px;
    min-width: 0;
  }
  h1 {
    margin: 0;
    font-size: clamp(22px, 3vw, 34px);
    font-weight: 800;
    letter-spacing: -0.02em;
    line-height: 1.15;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .artist {
    margin-top: 8px;
    font-size: 17px;
    color: var(--text-2);
    font-weight: 600;
  }
  .album {
    margin-top: 4px;
    font-size: 14.5px;
    color: var(--text-3);
  }
  .link:hover {
    text-decoration: underline;
    color: #fff;
  }
  .times {
    display: flex;
    justify-content: space-between;
    font-size: 12.5px;
    color: var(--text-3);
    font-variant-numeric: tabular-nums;
    margin-top: 2px;
  }
  .seek :global(.fill),
  .volume :global(.fill) {
    background: #fff;
  }
  .seek :global(.track),
  .volume :global(.track) {
    background: rgba(255, 255, 255, 0.25);
  }
  .controls {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .icon-btn {
    color: var(--text-2);
  }
  .icon-btn.big {
    width: 56px;
    height: 56px;
    color: #fff;
  }
  .icon-btn.active {
    color: color-mix(in srgb, var(--accent) 60%, #fff);
  }
  .play {
    display: grid;
    place-items: center;
    width: 72px;
    height: 72px;
    border-radius: 50%;
    background: #fff;
    color: #111;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
    transition: transform 0.15s var(--ease);
  }
  .play:active {
    transform: scale(0.94);
  }
  .volume {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .extras {
    display: flex;
    justify-content: center;
    gap: 18px;
  }
  .upnext {
    background: rgba(0, 0, 0, 0.22);
    border-radius: var(--radius);
    padding: 10px;
  }
  .label {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-3);
    padding: 2px 6px 8px;
  }
  .next-row {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 6px;
    border-radius: 8px;
    text-align: left;
    min-width: 0;
  }
  .next-row:hover {
    background: var(--surface-hover);
  }
  .thumb {
    width: 38px;
    flex-shrink: 0;
  }
  .small {
    font-size: 12.5px;
  }
  .empty {
    flex: 1;
    color: var(--text-3);
  }

  @media (max-width: 799px), (max-aspect-ratio: 1/1) {
    .body {
      grid-template-columns: 1fr;
      align-content: start;
      gap: 26px;
      padding: 8px 24px calc(24px + var(--safe-bottom));
      overflow-y: auto;
    }
    .art {
      justify-self: center;
      width: min(100%, 46vh);
    }
    .upnext {
      display: none;
    }
  }
</style>
