export const ui = $state({
  nowPlaying: false,
  queuePanel: false, // desktop side panel
  sheet: null, // { title, subtitle, image, actions: [{ icon, label, run, danger }] }
  dialog: null, // { kind: 'prompt' | 'playlist' | 'confirm', ...props, resolve }
  coverPicker: null, // { uri, kind, title, query }
});

/** Let the user pick a cover for `uri` by hand (see CoverPicker.svelte). */
export function openCoverPicker(target) {
  ui.coverPicker = target;
}

export function openSheet(sheet) {
  ui.sheet = sheet;
}

export function closeSheet() {
  ui.sheet = null;
}

function dialog(kind, props) {
  return new Promise((resolve) => {
    ui.dialog = {
      kind,
      ...props,
      resolve: (value) => {
        ui.dialog = null;
        resolve(value);
      },
    };
  });
}

export const prompt = (props) => dialog('prompt', props);
export const confirm = (props) => dialog('confirm', props);
export const pickPlaylist = (props = {}) => dialog('playlist', props);
