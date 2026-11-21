// Melody's own HTTP API (config, snapcast proxy, art cache).

let configPromise;

export function getConfig() {
  configPromise ??= fetch('api/config')
    .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.statusText))))
    .catch(() => ({
      title: 'Melody',
      version: '',
      album_uris: ['local:directory?type=album'],
      artist_uris: ['local:directory?type=artist'],
      snapcast: false,
      web_art: [],
    }));
  return configPromise;
}

export async function clearArtCache() {
  const r = await fetch('api/art/clear', { method: 'POST' });
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

let snapId = 1;
export async function snapcast(method, params) {
  const r = await fetch('api/snapcast', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jsonrpc: '2.0', id: snapId++, method, params }),
  });
  if (!r.ok) throw new Error(`Snapcast: ${r.status} ${r.statusText}`);
  const data = await r.json();
  if (data.error) throw new Error(data.error.message || 'Snapcast error');
  return data.result;
}

async function json(r) {
  if (r.ok) return r.json();
  const body = await r.json().catch(() => null);
  throw new Error(body?.error || `${r.status} ${r.statusText}`);
}

/** UI preferences shared by all clients (stored on the server). */
export const getPrefs = () => fetch('api/prefs').then(json);

export const savePrefs = (prefs) =>
  fetch('api/prefs', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(prefs),
  }).then(json);

// ---------------------------------------------------------- cover overrides

export const getArtOverrides = () => fetch('api/art/overrides').then(json);

export function getArtCandidates(uri, kind, q) {
  const params = new URLSearchParams({ uri, kind: kind || 'album', q: q || '' });
  return fetch('api/art/candidates?' + params).then(json);
}

/** `image` is a File/Blob (upload) or a URL string. */
export function setArtOverride(uri, image) {
  const body = typeof image === 'string' ? JSON.stringify({ url: image }) : image;
  const type = typeof image === 'string' ? 'application/json' : image.type || 'image/jpeg';
  return fetch('api/art/override?' + new URLSearchParams({ uri }), {
    method: 'POST',
    headers: { 'Content-Type': type },
    body,
  }).then(json);
}

export const removeArtOverride = (uri) =>
  fetch('api/art/override?' + new URLSearchParams({ uri }), { method: 'DELETE' }).then(json);

// ------------------------------------------------------------- local scan

export const getScanStatus = () => fetch('api/local/scan').then(json);

export const startScan = (full = false) =>
  fetch('api/local/scan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ full }),
  }).then(json);
