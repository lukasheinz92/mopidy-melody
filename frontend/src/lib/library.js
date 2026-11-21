// Library access + queue actions, following the call patterns of Mopidy-Mobile.

import { rpc } from './rpc.js';
import { settings } from './settings.svelte.js';
import { toast, toastError } from './toast.svelte.js';
import { player } from './player.svelte.js';

const call = (method, params) => rpc.call(method, params);

// Small TTL caches; browsing back and forth should be instant.
const cache = new Map();
function cached(key, ttl, fn) {
  const hit = cache.get(key);
  if (hit && Date.now() - hit.at < ttl) return hit.promise;
  const promise = fn().catch((e) => {
    cache.delete(key);
    throw e;
  });
  cache.set(key, { at: Date.now(), promise });
  return promise;
}

export function invalidate(prefix = '') {
  for (const key of cache.keys()) if (key.startsWith(prefix)) cache.delete(key);
}

export const browse = (uri) =>
  cached('browse:' + uri, 5 * 60000, () => call('core.library.browse', { uri: uri ?? null }));

export const lookup = (uri) =>
  cached('lookup:' + uri, 5 * 60000, async () => {
    const result = await call('core.library.lookup', { uris: [uri] });
    return result[uri] || [];
  });

/** Batch lookup, used to enrich album cards with artist/year. */
export async function lookupMany(uris) {
  const missing = uris.filter((u) => !cache.has('lookup:' + u));
  if (missing.length) {
    const result = await call('core.library.lookup', { uris: missing });
    for (const uri of missing) {
      cache.set('lookup:' + uri, { at: Date.now(), promise: Promise.resolve(result[uri] || []) });
    }
  }
  return Object.fromEntries(await Promise.all(uris.map(async (u) => [u, await lookup(u)])));
}

export function search(query, scheme) {
  return call('core.library.search', {
    query: { any: [query] },
    uris: scheme ? [scheme + ':'] : null,
  });
}

export const playlists = () =>
  cached('playlists:' + player.playlistsVersion, 60000, () => call('core.playlists.as_list'));

export const playlist = (uri) =>
  cached(`playlist:${player.playlistsVersion}:${uri}`, 60000, () =>
    call('core.playlists.lookup', { uri })
  );

export const playlistSchemes = () =>
  cached('playlist-schemes', 10 * 60000, () => call('core.playlists.get_uri_schemes'));

// ------------------------------------------------------------------ queue

const isPlaylistUri = (uri) => uri.startsWith('m3u:') || /^[a-z]+:playlist:/.test(uri);

/** Playlists can't be added via the library; expand them to their items. */
async function expand(uris) {
  if (!uris.some(isPlaylistUri)) return uris;
  const parts = await Promise.all(
    uris.map(async (uri) => {
      if (!isPlaylistUri(uri)) return [uri];
      const refs = await call('core.playlists.get_items', { uri });
      return (refs || []).map((r) => r.uri);
    })
  );
  return parts.flat();
}

async function add(uris, at_position = null) {
  return call('core.tracklist.add', { uris: await expand(uris), at_position });
}

async function currentIndex() {
  const tl = player.tlTrack;
  if (!tl) return null;
  return call('core.tracklist.index', { tlid: tl.tlid });
}

/** Replace the queue with `uris` and start playing at `index`. */
export async function playUris(uris, index = 0) {
  try {
    const expanded = await expand(uris);
    await call('core.tracklist.clear');
    const added = await call('core.tracklist.add', { uris: expanded });
    if (!added.length) return toast('Nothing playable found', { error: true });
    const target = added[Math.min(index, added.length - 1)];
    await call('core.playback.play', { tlid: target.tlid });
  } catch (e) {
    toastError(e, 'Could not play');
  }
}

/** Insert after the current track and start playing it right away. */
export async function playNow(uris) {
  try {
    const idx = await currentIndex();
    const added = await add(uris, idx == null ? null : idx + 1);
    if (added.length) await call('core.playback.play', { tlid: added[0].tlid });
  } catch (e) {
    toastError(e, 'Could not play');
  }
}

export async function playNext(uris) {
  try {
    const idx = await currentIndex();
    const added = await add(uris, idx == null ? null : idx + 1);
    toast(added.length === 1 ? 'Playing next' : `${added.length} tracks play next`);
  } catch (e) {
    toastError(e, 'Could not add');
  }
}

export async function addToQueue(uris) {
  try {
    const added = await add(uris);
    toast(added.length === 1 ? 'Added to queue' : `Added ${added.length} tracks to queue`);
  } catch (e) {
    toastError(e, 'Could not add');
  }
}

export async function shuffleUris(uris) {
  await playUris(uris, 0);
  try {
    await call('core.tracklist.shuffle');
    const tracks = await call('core.tracklist.get_tl_tracks');
    if (tracks.length) await call('core.playback.play', { tlid: tracks[0].tlid });
  } catch (e) {
    toastError(e);
  }
}

/** What happens when a track row in a list is tapped (configurable).
 *  Only ever the tapped song: the whole list is queued via its Play button. */
export function tapTrack(uri) {
  if (settings.tapAction === 'play-now') return playNow([uri]);
  if (settings.tapAction === 'add') return addToQueue([uri]);
  return playUris([uri]);
}

export const tracklist = {
  remove: (tlids) => call('core.tracklist.remove', { criteria: { tlid: tlids } }),
  move: (start, end, to_position) => call('core.tracklist.move', { start, end, to_position }),
  clear: () => call('core.tracklist.clear'),
  shuffle: () => call('core.tracklist.shuffle'),
};

// -------------------------------------------------------------- playlists

async function editableScheme() {
  const schemes = await playlistSchemes();
  return schemes.includes('m3u') ? 'm3u' : schemes[0];
}

export async function createPlaylist(name, tracks = []) {
  const created = await call('core.playlists.create', { name, uri_scheme: await editableScheme() });
  if (!created) throw new Error('Backend refused to create the playlist');
  const saved = tracks.length
    ? await call('core.playlists.save', { playlist: { ...created, tracks } })
    : created;
  invalidate('playlists:');
  return saved;
}

export async function addToPlaylist(playlistUri, uris) {
  const pl = await call('core.playlists.lookup', { uri: playlistUri });
  uris = await expand(uris);
  const looked = await call('core.library.lookup', { uris });
  const tracks = uris.flatMap((u) => looked[u] || []);
  const saved = await call('core.playlists.save', {
    playlist: { ...pl, tracks: [...(pl.tracks || []), ...tracks] },
  });
  invalidate('playlist');
  return saved;
}

export async function removeFromPlaylist(pl, index) {
  const tracks = [...(pl.tracks || [])];
  tracks.splice(index, 1);
  const saved = await call('core.playlists.save', { playlist: { ...pl, tracks } });
  invalidate('playlist');
  return saved;
}

export async function deletePlaylist(uri) {
  const ok = await call('core.playlists.delete', { uri });
  invalidate('playlist');
  return ok;
}

export function isEditablePlaylist(uri) {
  return (uri || '').startsWith('m3u:');
}
