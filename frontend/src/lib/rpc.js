// Minimal Mopidy JSON-RPC client over WebSocket (same protocol mopidy.js uses).

const CALL_TIMEOUT = 30000;

export class MopidyRpc {
  constructor(url) {
    this.url = url;
    this.ws = null;
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = new Map();
    this.backoff = 500;
    this.closedByUser = false;
  }

  connect() {
    this.closedByUser = false;
    const ws = new WebSocket(this.url);
    this.ws = ws;
    ws.onopen = () => {
      this.backoff = 500;
      this.emit('state:online');
    };
    ws.onclose = () => {
      if (this.ws !== ws) return;
      this.ws = null;
      for (const { reject, timer } of this.pending.values()) {
        clearTimeout(timer);
        reject(new Error('Connection lost'));
      }
      this.pending.clear();
      this.emit('state:offline');
      if (!this.closedByUser) {
        setTimeout(() => this.connect(), this.backoff);
        this.backoff = Math.min(this.backoff * 2, 10000);
      }
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (msg) => this.handle(JSON.parse(msg.data));
  }

  close() {
    this.closedByUser = true;
    this.ws?.close();
  }

  get online() {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  handle(data) {
    if (data.event) {
      this.emit('event:' + data.event, data);
      this.emit('event', data);
      return;
    }
    const call = this.pending.get(data.id);
    if (!call) return;
    this.pending.delete(data.id);
    clearTimeout(call.timer);
    if (data.error) {
      const err = new Error(data.error.data?.message || data.error.message);
      err.data = data.error;
      call.reject(err);
    } else {
      call.resolve(data.result);
    }
  }

  /** call('core.library.browse', { uri: null }) */
  call(method, params = {}) {
    if (!this.online) return Promise.reject(new Error('Not connected'));
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Timeout calling ${method}`));
      }, CALL_TIMEOUT);
      this.pending.set(id, { resolve, reject, timer });
      this.ws.send(JSON.stringify({ jsonrpc: '2.0', id, method, params }));
    });
  }

  on(name, fn) {
    if (!this.listeners.has(name)) this.listeners.set(name, new Set());
    this.listeners.get(name).add(fn);
    return () => this.listeners.get(name)?.delete(fn);
  }

  emit(name, data) {
    for (const fn of this.listeners.get(name) || []) {
      try {
        fn(data);
      } catch (e) {
        console.error(e);
      }
    }
  }
}

function wsUrl() {
  // The app lives at <base>/melody/, Mopidy's socket at <base>/mopidy/ws
  // (the Vite dev server serves the app at / and proxies /mopidy).
  const rel = import.meta.env.DEV ? '/mopidy/ws' : '../mopidy/ws';
  const url = new URL(rel, new URL('.', location.href));
  url.protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return url.toString();
}

export const rpc = new MopidyRpc(wsUrl());
