// Preferences shared by every client, stored on the server (/api/prefs) so
// they live in Mopidy's data dir rather than in one browser.

import { getPrefs, savePrefs } from './api.js';
import { toastError } from './toast.svelte.js';

export const prefs = $state({
  loaded: false,
  nav: { order: [], hidden: [] }, // ids from NAV_ITEMS
});

export function loadPrefs() {
  return getPrefs()
    .then((data) => {
      if (data?.nav) prefs.nav = { order: data.nav.order || [], hidden: data.nav.hidden || [] };
    })
    .catch(() => {})
    .finally(() => (prefs.loaded = true));
}

let timer;
/** Persist after a short pause so quick reorders are saved once. */
export function persistPrefs() {
  clearTimeout(timer);
  timer = setTimeout(() => {
    savePrefs({ nav: $state.snapshot(prefs.nav) }).catch((e) =>
      toastError(e, 'Could not save settings')
    );
  }, 400);
}
