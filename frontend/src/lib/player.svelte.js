import { rpc } from './rpc.js';

export const player = $state({
  online: false,
  connecting: true,
  state: 'stopped', // playing | paused | stopped
  tlTrack: null,
  streamTitle: null,
  position: 0,
  positionAt: 0,
  volume: null,
  mute: false,
  random: false,
  repeat: false,
  single: false,
  consume: false,
  tracklist: [],
  uriSchemes: [],
  version: '',
  playlistsVersion: 0,
});

/** Ticks while playing so position bars can interpolate between syncs. */
export const clock = $state({ now: Date.now() });
setInterval(() => {
  if (player.state === 'playing') clock.now = Date.now();
}, 250);

export function currentTrack() {
  return player.tlTrack?.track ?? null;
}

export function position() {
  const length = player.tlTrack?.track?.length ?? Infinity;
  const elapsed = player.state === 'playing' ? Math.max(0, clock.now - player.positionAt) : 0;
  return Math.min(player.position + elapsed, length);
}

function setPosition(ms) {
  player.position = ms ?? 0;
  player.positionAt = Date.now();
  clock.now = player.positionAt;
}

const call = (method, params) => rpc.call(method, params);

async function syncPosition() {
  setPosition(await call('core.playback.get_time_position'));
}

async function syncTracklist() {
  const [tracks, current] = await Promise.all([
    call('core.tracklist.get_tl_tracks'),
    call('core.playback.get_current_tl_track'),
  ]);
  player.tracklist = tracks;
  player.tlTrack = current;
}

async function syncOptions() {
  const [random, repeat, single, consume] = await Promise.all([
    call('core.tracklist.get_random'),
    call('core.tracklist.get_repeat'),
    call('core.tracklist.get_single'),
    call('core.tracklist.get_consume'),
  ]);
  Object.assign(player, { random, repeat, single, consume });
}

async function syncAll() {
  const [state, volume, mute, streamTitle, uriSchemes, version] = await Promise.all([
    call('core.playback.get_state'),
    call('core.mixer.get_volume'),
    call('core.mixer.get_mute'),
    call('core.playback.get_stream_title'),
    call('core.get_uri_schemes'),
    call('core.get_version'),
  ]);
  Object.assign(player, { state, volume, mute, uriSchemes, version });
  await Promise.all([syncTracklist(), syncOptions(), syncPosition()]);
  player.streamTitle = player.tlTrack?.track?.length ? null : streamTitle;
}

rpc.on('state:online', async () => {
  player.online = true;
  player.connecting = false;
  try {
    await syncAll();
  } catch (e) {
    console.error('Initial sync failed', e);
  }
});
rpc.on('state:offline', () => {
  player.online = false;
});

rpc.on('event:track_playback_started', ({ tl_track }) => {
  player.tlTrack = tl_track;
  player.streamTitle = null;
  player.state = 'playing';
  setPosition(0);
});
rpc.on('event:track_playback_paused', ({ time_position }) => {
  player.state = 'paused';
  setPosition(time_position);
});
rpc.on('event:track_playback_resumed', ({ time_position }) => {
  player.state = 'playing';
  setPosition(time_position);
});
rpc.on('event:playback_state_changed', ({ new_state }) => {
  player.state = new_state;
  if (new_state === 'stopped') setPosition(0);
  else syncPosition().catch(() => {});
});
rpc.on('event:seeked', ({ time_position }) => setPosition(time_position));
rpc.on('event:tracklist_changed', () => syncTracklist().catch(() => {}));
rpc.on('event:options_changed', () => syncOptions().catch(() => {}));
rpc.on('event:volume_changed', ({ volume }) => (player.volume = volume));
rpc.on('event:mute_changed', ({ mute }) => (player.mute = mute));
rpc.on('event:stream_title_changed', ({ title }) => {
  // Only streams (no length) have meaningful stream titles; for files the
  // event can arrive late and belong to the previous track.
  if (!player.tlTrack?.track?.length) player.streamTitle = title;
});
for (const ev of ['playlists_loaded', 'playlist_changed', 'playlist_deleted']) {
  rpc.on('event:' + ev, () => player.playlistsVersion++);
}

// Re-sync the position now and then; the server clock is the source of truth.
setInterval(() => {
  if (player.online && player.state === 'playing') syncPosition().catch(() => {});
}, 15000);
document.addEventListener('visibilitychange', () => {
  if (!document.hidden && player.online) syncAll().catch(() => {});
});

// ---------------------------------------------------------------- controls

export const controls = {
  play: (tlid) => call('core.playback.play', tlid != null ? { tlid } : {}),
  pause: () => call('core.playback.pause'),
  resume: () => call('core.playback.resume'),
  toggle() {
    if (player.state === 'playing') return this.pause();
    if (player.state === 'paused') return this.resume();
    return this.play();
  },
  stop: () => call('core.playback.stop'),
  next: () => call('core.playback.next'),
  previous() {
    // Like most players: restart the track unless we're at its very beginning.
    if (position() > 4000) return this.seek(0);
    return call('core.playback.previous');
  },
  seek(ms) {
    setPosition(ms);
    return call('core.playback.seek', { time_position: Math.round(ms) });
  },
  setVolume: throttle((volume) => {
    call('core.mixer.set_volume', { volume: Math.round(volume) });
  }, 120),
  toggleMute: () => call('core.mixer.set_mute', { mute: !player.mute }),
  setRandom: (value) => call('core.tracklist.set_random', { value }),
  setConsume: (value) => call('core.tracklist.set_consume', { value }),
  async cycleRepeat() {
    // off -> repeat all -> repeat one -> off
    if (!player.repeat) {
      await call('core.tracklist.set_repeat', { value: true });
      await call('core.tracklist.set_single', { value: false });
    } else if (!player.single) {
      await call('core.tracklist.set_single', { value: true });
    } else {
      await call('core.tracklist.set_repeat', { value: false });
      await call('core.tracklist.set_single', { value: false });
    }
  },
};

function throttle(fn, wait) {
  let last = 0;
  let timer = null;
  let pending;
  return (...args) => {
    pending = args;
    const now = Date.now();
    if (now - last >= wait) {
      last = now;
      fn(...pending);
    } else if (!timer) {
      timer = setTimeout(() => {
        timer = null;
        last = Date.now();
        fn(...pending);
      }, wait - (now - last));
    }
  };
}
