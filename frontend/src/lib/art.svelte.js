// URLs for the server-side cover art resolver (/melody/api/art).

import { getArtOverrides } from './api.js';

// Images are cached by the browser for a week; the override epoch in every
// URL makes all clients refetch after a cover was changed by hand.
export const artState = $state({ epoch: 0, overrides: {} });

export function loadArtOverrides() {
  return getArtOverrides()
    .then(applyArtOverrides)
    .catch(() => {});
}

export function applyArtOverrides({ epoch, uris }) {
  artState.epoch = epoch || 0;
  artState.overrides = uris || {};
}

export function artUrl(uri, { size = 256, kind, artist, album, title } = {}) {
  if (!uri) return null;
  const params = new URLSearchParams({ uri, size: String(size) });
  if (kind) params.set('kind', kind);
  if (artist) params.set('artist', artist);
  if (album) params.set('album', album);
  if (title) params.set('title', title);
  if (artState.epoch) params.set('v', String(artState.epoch));
  return 'api/art?' + params;
}

/** The URI whose cover a track shows: its album (shared cache entry) or itself. */
export function trackArtTarget(track) {
  const artist = track.album?.artists?.[0]?.name || track.artists?.[0]?.name;
  const hints = { artist, album: track.album?.name, title: track.name };
  if (track.album?.uri) return { uri: track.album.uri, kind: 'album', ...hints };
  return { uri: track.uri, kind: 'track', ...hints };
}

/** Art for a track: prefer its album (shared cache entry) with name hints. */
export function trackArt(track, size = 256) {
  if (!track) return null;
  const { uri, ...hints } = trackArtTarget(track);
  return artUrl(uri, { ...hints, size });
}
