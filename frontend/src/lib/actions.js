// Action lists for the bottom sheet / context menu.

import {
  addToPlaylist,
  addToQueue,
  createPlaylist,
  playNext,
  playNow,
  playUris,
  shuffleUris,
} from './library.js';
import { navigate } from './router.svelte.js';
import { openCoverPicker, pickPlaylist, prompt } from './ui.svelte.js';
import { toast, toastError } from './toast.svelte.js';
import { trackTitle, trackArtist } from './format.js';
import { trackArt, trackArtTarget, artUrl } from './art.svelte.js';

export async function saveToPlaylist(uris) {
  const choice = await pickPlaylist({ title: 'Add to playlist' });
  if (!choice) return;
  try {
    if (choice === 'new') {
      const name = await prompt({ title: 'New playlist', placeholder: 'Playlist name' });
      if (!name) return;
      const pl = await createPlaylist(name);
      await addToPlaylist(pl.uri, uris);
      toast(`Saved to “${name}”`);
    } else {
      await addToPlaylist(choice.uri, uris);
      toast(`Added to “${choice.name}”`);
    }
  } catch (e) {
    toastError(e, 'Could not save');
  }
}

function coverAction(kind, target) {
  return {
    icon: 'image',
    label: kind === 'artist' ? 'Change picture…' : 'Change cover…',
    run: () => openCoverPicker({ kind, ...target }),
  };
}

export function trackSheet(track, extra = []) {
  const uris = [track.uri];
  const albumArtist = track.album?.artists?.[0] || track.artists?.[0];
  const actions = [
    { icon: 'play', label: 'Play now', run: () => playNow(uris) },
    { icon: 'playNext', label: 'Play next', run: () => playNext(uris) },
    { icon: 'queue', label: 'Add to queue', run: () => addToQueue(uris) },
    { icon: 'playlistAdd', label: 'Add to playlist…', run: () => saveToPlaylist(uris) },
  ];
  if (track.album?.uri) {
    actions.push({
      icon: 'album',
      label: 'Go to album',
      run: () => navigate('/album', { uri: track.album.uri }),
    });
  }
  for (const artist of track.artists || []) {
    if (artist.uri) {
      actions.push({
        icon: 'artist',
        label: `Go to ${artist.name || 'artist'}`,
        run: () => navigate('/artist', { uri: artist.uri, name: artist.name }),
      });
    }
  }
  const art = trackArtTarget(track);
  actions.push(
    coverAction(art.kind, {
      uri: art.uri,
      title: art.album || art.title || trackTitle(track),
      query: [art.artist, art.album || art.title].filter(Boolean).join(' '),
    })
  );
  return {
    title: trackTitle(track),
    subtitle: [trackArtist(track), track.album?.name].filter(Boolean).join(' · '),
    image: trackArt(track),
    actions: [...actions, ...extra],
    fallbackArtist: albumArtist?.name,
  };
}

export function collectionSheet({ uri, name, subtitle, kind = 'album', uris }) {
  const list = uris || [uri];
  return {
    title: name,
    subtitle,
    image: artUrl(uri, { kind }),
    actions: [
      { icon: 'play', label: 'Play', run: () => playUris(list) },
      { icon: 'shuffle', label: 'Shuffle', run: () => shuffleUris(list) },
      { icon: 'playNext', label: 'Play next', run: () => playNext(list) },
      { icon: 'queue', label: 'Add to queue', run: () => addToQueue(list) },
      { icon: 'playlistAdd', label: 'Add to playlist…', run: () => saveToPlaylist(list) },
      coverAction(kind, {
        uri,
        title: name,
        // subtitle is e.g. "Artist · 2012"; its first part helps the web search.
        query: kind === 'artist' ? name : [subtitle?.split(' · ')[0], name].filter(Boolean).join(' '),
      }),
    ],
  };
}
