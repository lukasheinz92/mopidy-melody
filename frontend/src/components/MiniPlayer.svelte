<script>
  // Mobile mini player above the tab bar; tap opens the full player.
  import Cover from './Cover.svelte';
  import Icon from './Icon.svelte';
  import { player, controls, position, currentTrack } from '../lib/player.svelte.js';
  import { trackArt } from '../lib/art.svelte.js';
  import { trackTitle, trackArtist } from '../lib/format.js';
  import { ui } from '../lib/ui.svelte.js';

  const track = $derived(currentTrack());
  const pct = $derived(track?.length ? (position() / track.length) * 100 : 0);
</script>

{#if track}
  <div
    class="mini"
    role="button"
    tabindex="0"
    onclick={() => (ui.nowPlaying = true)}
    onkeydown={(e) => e.key === 'Enter' && (ui.nowPlaying = true)}
  >
    <div class="progress" style="width:{pct}%"></div>
    <div class="art"><Cover src={trackArt(track, 256)} icon="note" eager /></div>
    <div class="meta">
      <div class="title ellipsis">{player.streamTitle || trackTitle(track)}</div>
      <div class="sub ellipsis">
        {player.streamTitle ? track.name : trackArtist(track)}
      </div>
    </div>
    <button
      class="icon-btn"
      aria-label="Play/Pause"
      onclick={(e) => {
        e.stopPropagation();
        controls.toggle();
      }}
    >
      <Icon name={player.state === 'playing' ? 'pause' : 'play'} size={30} />
    </button>
    <button
      class="icon-btn"
      aria-label="Next"
      onclick={(e) => {
        e.stopPropagation();
        controls.next();
      }}
    >
      <Icon name="next" size={26} />
    </button>
  </div>
{/if}

<style>
  .mini {
    position: relative;
    display: flex;
    align-items: center;
    gap: 12px;
    height: var(--mini-h);
    margin: 0 8px 6px;
    padding: 0 6px 0 8px;
    border-radius: 12px;
    background: color-mix(in srgb, var(--surface-2) 92%, var(--accent) 8%);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    overflow: hidden;
    cursor: pointer;
  }
  .progress {
    position: absolute;
    left: 0;
    bottom: 0;
    height: 2px;
    background: var(--accent);
    transition: width 0.25s linear;
  }
  .art {
    width: 46px;
  }
  .art :global(.cover) {
    border-radius: 6px;
  }
  .meta {
    flex: 1;
    min-width: 0;
  }
  .title {
    font-weight: 650;
    font-size: 14.5px;
  }
  .sub {
    font-size: 13px;
    color: var(--text-2);
    margin-top: 1px;
  }
  .icon-btn {
    color: var(--text);
    width: 44px;
    height: 44px;
  }
</style>
