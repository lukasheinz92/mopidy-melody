import { prefs } from './prefs.svelte.js';

// Every menu entry; the default order is the order here.
export const NAV_ITEMS = [
  // One page: search field on top, browse sources below while it's empty.
  { id: 'browse', path: '/browse', icon: 'search', label: 'Browse & Search', short: 'Browse', match: ['/browse', '/search'] },
  { id: 'artists', path: '/artists', icon: 'artist', label: 'Artists', match: ['/artists', '/artist'] },
  { id: 'albums', path: '/albums', icon: 'album', label: 'Albums', match: ['/albums', '/album'] },
  { id: 'playlists', path: '/playlists', icon: 'playlist', label: 'Playlists', match: ['/playlists', '/playlist'] },
  { id: 'queue', path: '/queue', icon: 'queue', label: 'Queue' },
  { id: 'rooms', path: '/rooms', icon: 'speaker', label: 'Rooms', snapcast: true },
  { id: 'settings', path: '/settings', icon: 'settings', label: 'Settings', required: true },
];

/** Bottom tab bar: this many items, then "More" for the rest. */
export const TAB_COUNT = 4;

/** All items available on this server, in the user's order. */
export function orderedItems(config) {
  const available = NAV_ITEMS.filter((i) => !i.snapcast || config?.snapcast);
  const rank = (i) => {
    const r = prefs.nav.order.indexOf(i.id);
    return r < 0 ? prefs.nav.order.length + NAV_ITEMS.indexOf(i) : r;
  };
  return [...available].sort((a, b) => rank(a) - rank(b));
}

export const isHidden = (item) => !item.required && prefs.nav.hidden.includes(item.id);

export function navItems(config) {
  return orderedItems(config).filter((i) => !isHidden(i));
}

/** { tabs, more }: the first items as tabs, the rest behind a "More" tab. */
export function tabItems(config) {
  const items = navItems(config);
  if (items.length <= TAB_COUNT + 1) return { tabs: items, more: [] };
  return { tabs: items.slice(0, TAB_COUNT), more: items.slice(TAB_COUNT) };
}

export function isActive(item, path) {
  return (item.match || [item.path]).includes(path);
}
