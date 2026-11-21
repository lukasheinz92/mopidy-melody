export function duration(ms) {
  if (ms == null || !isFinite(ms)) return '';
  const s = Math.floor(ms / 1000);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = String(s % 60).padStart(2, '0');
  return h ? `${h}:${String(m).padStart(2, '0')}:${sec}` : `${m}:${sec}`;
}

export function longDuration(ms) {
  const min = Math.round((ms || 0) / 60000);
  if (min < 60) return `${min} min`;
  return `${Math.floor(min / 60)} h ${min % 60} min`;
}

export function artistNames(artists) {
  return (artists || []).map((a) => a.name).filter(Boolean).join(', ');
}

export function year(date) {
  return date ? String(date).slice(0, 4) : '';
}

const SOURCE_NAMES = {
  local: 'Local',
  file: 'Files',
  jellyfin: 'Jellyfin',
  youtube: 'YouTube',
  yt: 'YouTube',
  ytmusic: 'YouTube Music',
  invidious: 'Invidious',
  radiobrowser: 'Radio',
  spotify: 'Spotify',
  m3u: 'Playlists',
  tunein: 'TuneIn',
  soundcloud: 'SoundCloud',
  podcast: 'Podcasts',
};

export function scheme(uri) {
  return (uri || '').split(':')[0];
}

export function sourceName(uriOrScheme) {
  const s = scheme(uriOrScheme);
  return SOURCE_NAMES[s] || s.charAt(0).toUpperCase() + s.slice(1);
}

export function plural(n, word) {
  return `${n} ${word}${n === 1 ? '' : 's'}`;
}

// Untagged files show up as "ARTIST - Title.mp3"; split that for display.
function splitName(name) {
  const clean = (name || '').replace(/\.(mp3|flac|ogg|opus|m4a|aac|wav|wma)$/i, '');
  const m = clean.match(/^(.+?)\s+[-–]\s+(.+)$/);
  return m ? { artist: m[1].trim(), title: m[2].trim() } : { artist: '', title: clean };
}

export function trackTitle(track) {
  if (!track) return '';
  if (track.artists?.length || !track.name) return track.name || track.uri;
  return splitName(track.name).title;
}

export function trackArtist(track) {
  if (!track) return '';
  if (track.artists?.length) return artistNames(track.artists);
  return splitName(track.name).artist;
}
