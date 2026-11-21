// Tiny hash router: #/album?uri=local:album:...

function parse() {
  // '/' (no hash) is redirected to the first menu item by App.svelte.
  const hash = location.hash.replace(/^#/, '') || '/';
  const [path, query = ''] = hash.split('?');
  return { path, params: Object.fromEntries(new URLSearchParams(query)) };
}

export const route = $state(parse());

window.addEventListener('hashchange', () => {
  Object.assign(route, parse());
  document.querySelector('main')?.scrollTo({ top: 0 });
});

export function href(path, params = {}) {
  const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== ''));
  const query = new URLSearchParams(clean).toString();
  return '#' + path + (query ? '?' + query : '');
}

export function navigate(path, params) {
  location.hash = href(path, params).slice(1);
}
