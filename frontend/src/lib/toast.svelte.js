export const toasts = $state([]);
let id = 0;

export function toast(message, { error = false, timeout = 2600 } = {}) {
  const t = { id: ++id, message, error };
  toasts.push(t);
  setTimeout(() => {
    const i = toasts.findIndex((x) => x.id === t.id);
    if (i >= 0) toasts.splice(i, 1);
  }, timeout);
}

export function toastError(e, prefix = 'Error') {
  console.error(e);
  toast(`${prefix}: ${e?.message || e}`, { error: true, timeout: 5000 });
}
