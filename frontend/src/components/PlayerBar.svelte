<script>
  // Desktop player bar (bottom, full width).
  import Cover from './Cover.svelte';
  import Icon from './Icon.svelte';
  import Slider from './Slider.svelte';
  import { player, controls, position, currentTrack } from '../lib/player.svelte.js';
  import { trackArt } from '../lib/art.svelte.js';
  import { duration, trackTitle, trackArtist } from '../lib/format.js';
  import { ui } from '../lib/ui.svelte.js';
  import { href } from '../lib/router.svelte.js';

  let { config } = $props();

  const track = $derived(currentTrack());
  const title = $derived(player.streamTitle || trackTitle(track));
  const subtitle = $derived(
    player.streamTitle ? track?.name : trackArtist(track) || track?.album?.name
  );
  const firstArtist = $derived(track?.artists?.find((a) => a.uri));
</script>

<footer class="bar">
  <div class="now">
    {#if track}
      <button class="art" onclick={() => (ui.nowPlaying = true)} aria-label="Open now playing">
        <Cover src={trackArt(track, 256)} icon="note" eager />
        <span class="expand"><Icon name="expand" size={18} /></span>
      </button>
      <div class="meta">
        {#if track.album?.uri}
          <a class="title ellipsis" href={href('/album', { uri: track.album.uri })}>{title}</a>
        {:else}
          <div class="title ellipsis">{title}</div>
        {/if}
        {#if firstArtist && !player.streamTitle}
          <a
            class="sub ellipsis"
            href={href('/artist', { uri: firstArtist.uri, name: firstArtist.name })}>{subtitle}</a
          >
        {:else}
          <div class="sub ellipsis">{subtitle || ''}</div>
        {/if}
      </div>
    {/if}
  </div>

  <div class="center">
    <div class="buttons">
      <button
        class="icon-btn"
        class:active={player.random}
        onclick={() => controls.setRandom(!player.random)}
        aria-label="Shuffle"
        title="Shuffle"><Icon name="shuffle" size={20} /></button
      >
      <button class="icon-btn" onclick={() => controls.previous()} aria-label="Previous">
        <Icon name="previous" />
      </button>
      <button class="play" onclick={() => controls.toggle()} aria-label="Play/Pause">
        <Icon name={player.state === 'playing' ? 'pause' : 'play'} size={26} />
      </button>
      <button
        class="icon-btn"
        onclick={() => controls.stop()}
        disabled={player.state === 'stopped'}
        aria-label="Stop"
        title="Stop"><Icon name="stop" size={20} /></button
      >
      <button class="icon-btn" onclick={() => controls.next()} aria-label="Next">
        <Icon name="next" />
      </button>
      <button
        class="icon-btn"
        class:active={player.repeat}
        onclick={() => controls.cycleRepeat()}
        aria-label="Repeat"
        title="Repeat"
      >
        <Icon name={player.single && player.repeat ? 'repeatOne' : 'repeat'} size={20} />
      </button>
    </div>
    <div class="seek">
      <span class="time">{duration(position())}</span>
      <Slider
        value={position()}
        max={track?.length || 0}
        disabled={!track?.length}
        onchange={(v) => controls.seek(v)}
        label="Seek"
      />
      <span class="time">{duration(track?.length)}</span>
    </div>
  </div>

  <div class="right">
    {#if config?.snapcast}
      <a class="icon-btn" href="#/rooms" title="Rooms" aria-label="Rooms">
        <Icon name="speaker" size={20} />
      </a>
    {/if}
    <button
      class="icon-btn"
      class:active={ui.queuePanel}
      onclick={() => (ui.queuePanel = !ui.queuePanel)}
      title="Queue"
      aria-label="Toggle queue"
    >
      <Icon name="queue" size={20} />
    </button>
    <button class="icon-btn" onclick={() => controls.toggleMute()} aria-label="Mute">
      <Icon name={player.mute || player.volume === 0 ? 'volumeOff' : 'volume'} size={20} />
    </button>
    <div class="volume">
      <Slider
        value={player.volume ?? 0}
        max={100}
        disabled={player.volume == null}
        oninput={(v) => controls.setVolume(v)}
        onchange={(v) => controls.setVolume(v)}
        label="Volume"
      />
    </div>
  </div>
</footer>

<style>
  .bar {
    display: grid;
    grid-template-columns: minmax(180px, 1fr) minmax(320px, 1.4fr) minmax(180px, 1fr);
    align-items: center;
    gap: 16px;
    height: var(--player-h);
    padding: 0 16px;
    background: var(--bg-elev);
    border-top: 1px solid var(--border);
  }
  .now {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
  }
  .art {
    position: relative;
    width: 58px;
    flex-shrink: 0;
    border-radius: var(--radius-sm);
    overflow: hidden;
  }
  .expand {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    background: rgba(0, 0, 0, 0.45);
    color: #fff;
    opacity: 0;
    transition: opacity 0.15s;
  }
  .art:hover .expand {
    opacity: 1;
  }
  .meta {
    min-width: 0;
  }
  .title {
    display: block;
    font-weight: 650;
  }
  .sub {
    display: block;
    font-size: 13px;
    color: var(--text-2);
    margin-top: 2px;
  }
  a.title:hover,
  a.sub:hover {
    text-decoration: underline;
  }
  .center {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
  }
  .buttons {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .play {
    display: grid;
    place-items: center;
    width: 42px;
    height: 42px;
    border-radius: 50%;
    background: var(--text);
    color: var(--bg);
    transition: transform 0.15s var(--ease);
  }
  .play:hover {
    transform: scale(1.06);
  }
  .play:active {
    transform: scale(0.94);
  }
  .seek {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    max-width: 640px;
  }
  .time {
    font-size: 12px;
    color: var(--text-3);
    font-variant-numeric: tabular-nums;
    min-width: 38px;
    text-align: center;
  }
  .right {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 2px;
  }
  .volume {
    width: 120px;
    display: flex;
  }
</style>
