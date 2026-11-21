const KEY = 'melody.settings';

const defaults = {
  theme: 'system', // system | light | dark
  accent: '#8b5cf6',
  tapAction: 'play', // play | play-now | add
  albumSource: null,
  artistSource: null,
  albumView: 'grid', // grid | list
  showOfflineRooms: false,
};

function load() {
  try {
    const saved = { ...defaults, ...JSON.parse(localStorage.getItem(KEY) || '{}') };
    // "play-list" (queue the whole list from the tapped song) is gone.
    if (saved.tapAction === 'play-list') saved.tapAction = 'play';
    return saved;
  } catch {
    return { ...defaults };
  }
}

export const settings = $state(load());

const media = matchMedia('(prefers-color-scheme: dark)');
const system = $state({ dark: media.matches });
media.addEventListener('change', (e) => (system.dark = e.matches));

export const ACCENTS = [
  '#8b5cf6', '#6366f1', '#3b82f6', '#06b6d4', '#14b8a6',
  '#22c55e', '#eab308', '#f97316', '#ef4444', '#ec4899',
];

$effect.root(() => {
  $effect(() => {
    localStorage.setItem(KEY, JSON.stringify(settings));
  });
  $effect(() => {
    const root = document.documentElement;
    const dark =
      settings.theme === 'dark' ||
      (settings.theme === 'system' && system.dark);
    root.dataset.theme = dark ? 'dark' : 'light';
    root.style.setProperty('--accent', settings.accent);
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute('content', dark ? '#0f0f14' : '#f6f6f9');
  });
});
