<script>
  // Snapcast multiroom control (proxied through /melody/api/snapcast).
  import Icon from '../components/Icon.svelte';
  import Slider from '../components/Slider.svelte';
  import { snapcast } from '../lib/api.js';
  import { player, controls } from '../lib/player.svelte.js';
  import { settings } from '../lib/settings.svelte.js';
  import { prompt } from '../lib/ui.svelte.js';
  import { toastError } from '../lib/toast.svelte.js';

  let server = $state(null);
  let error = $state(null);
  let busyUntil = 0; // skip polls right after local changes to avoid jitter

  async function refresh(force = false) {
    if (!force && Date.now() < busyUntil) return;
    try {
      const result = await snapcast('Server.GetStatus');
      if (force || Date.now() >= busyUntil) server = result.server;
      error = null;
    } catch (e) {
      error = e.message;
    }
  }

  $effect(() => {
    refresh(true);
    const id = setInterval(refresh, 3000);
    return () => clearInterval(id);
  });

  const streams = $derived(server?.streams || []);
  const groups = $derived(
    (server?.groups || [])
      .map((g) => ({
        ...g,
        visible: g.clients.filter((c) => c.connected || settings.showOfflineRooms),
      }))
      .filter((g) => g.visible.length)
  );
  const offlineCount = $derived(
    (server?.groups || []).flatMap((g) => g.clients).filter((c) => !c.connected).length
  );

  const clientName = (c) => c.config.name || c.host.name || c.id;

  function patchClient(id, fn) {
    for (const g of server?.groups || []) for (const c of g.clients) if (c.id === id) fn(c);
  }

  const volumeTimers = new Map();
  function setVolume(client, percent) {
    busyUntil = Date.now() + 1500;
    percent = Math.round(percent);
    patchClient(client.id, (c) => (c.config.volume.percent = percent));
    clearTimeout(volumeTimers.get(client.id));
    volumeTimers.set(
      client.id,
      setTimeout(() => {
        snapcast('Client.SetVolume', {
          id: client.id,
          volume: { muted: client.config.volume.muted, percent },
        }).catch((e) => toastError(e));
      }, 80)
    );
  }

  async function toggleClientMute(client) {
    busyUntil = Date.now() + 1500;
    const muted = !client.config.volume.muted;
    patchClient(client.id, (c) => (c.config.volume.muted = muted));
    try {
      await snapcast('Client.SetVolume', {
        id: client.id,
        volume: { muted, percent: client.config.volume.percent },
      });
    } catch (e) {
      toastError(e);
    }
  }

  async function toggleGroupMute(group) {
    busyUntil = Date.now() + 1500;
    const g = server.groups.find((x) => x.id === group.id);
    g.muted = !g.muted;
    try {
      await snapcast('Group.SetMute', { id: group.id, mute: g.muted });
    } catch (e) {
      toastError(e);
    }
  }

  async function setStream(group, stream_id) {
    try {
      await snapcast('Group.SetStream', { id: group.id, stream_id });
      refresh(true);
    } catch (e) {
      toastError(e);
    }
  }

  async function rename(client) {
    const name = await prompt({ title: 'Rename room', value: clientName(client), placeholder: 'Room name' });
    if (!name) return;
    try {
      await snapcast('Client.SetName', { id: client.id, name });
      refresh(true);
    } catch (e) {
      toastError(e);
    }
  }
</script>

<div class="page">
  <div class="page-header"><h1>Rooms</h1></div>

  <div class="card master">
    <div class="label"><Icon name="volume" size={20} /> Mopidy volume</div>
    <div class="vol">
      <button class="icon-btn" onclick={() => controls.toggleMute()} aria-label="Mute">
        <Icon name={player.mute ? 'volumeOff' : 'volume'} size={20} />
      </button>
      <Slider
        value={player.volume ?? 0}
        max={100}
        disabled={player.volume == null}
        oninput={(v) => controls.setVolume(v)}
        onchange={(v) => controls.setVolume(v)}
        label="Mopidy volume"
      />
      <span class="pct">{player.volume ?? '–'}</span>
    </div>
  </div>

  {#if error && !server}
    <div class="empty"><Icon name="offline" size={48} /><div>Snapcast unavailable: {error}</div></div>
  {:else if !server}
    <div class="spinner"></div>
  {:else}
    <div class="groups">
      {#each groups as group (group.id)}
        <div class="card group">
          <div class="ghead">
            <select
              value={group.stream_id}
              onchange={(e) => setStream(group, e.currentTarget.value)}
              aria-label="Stream"
            >
              {#each streams as s (s.id)}
                <option value={s.id}>{s.id}{s.status === 'playing' ? ' ▶' : ''}</option>
              {/each}
            </select>
            <button
              class="icon-btn"
              class:muted={group.muted}
              onclick={() => toggleGroupMute(group)}
              title={group.muted ? 'Unmute group' : 'Mute group'}
              aria-label="Mute group"
            >
              <Icon name={group.muted ? 'volumeOff' : 'volume'} size={20} />
            </button>
          </div>
          {#each group.visible as client (client.id)}
            <div class="client" class:offline={!client.connected}>
              <div class="cname">
                <span class="dot" class:on={client.connected}></span>
                <span class="ellipsis">{clientName(client)}</span>
                <button class="edit" onclick={() => rename(client)} aria-label="Rename"><Icon name="edit" size={15} /></button>
              </div>
              <div class="vol">
                <button class="icon-btn" class:muted={client.config.volume.muted} onclick={() => toggleClientMute(client)} aria-label="Mute">
                  <Icon name={client.config.volume.muted ? 'volumeOff' : 'volume'} size={20} />
                </button>
                <Slider
                  value={client.config.volume.percent}
                  max={100}
                  oninput={(v) => setVolume(client, v)}
                  onchange={(v) => setVolume(client, v)}
                  label="Volume {clientName(client)}"
                />
                <span class="pct">{client.config.volume.percent}</span>
              </div>
            </div>
          {/each}
        </div>
      {/each}
    </div>
    {#if offlineCount}
      <label class="toggle">
        <input type="checkbox" bind:checked={settings.showOfflineRooms} />
        Show {offlineCount} offline {offlineCount === 1 ? 'room' : 'rooms'}
      </label>
    {/if}
  {/if}
</div>

<style>
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
  }
  .master {
    margin-bottom: 20px;
  }
  .label {
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: 700;
    margin-bottom: 8px;
  }
  .groups {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 16px;
  }
  .ghead {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
  }
  select {
    flex: 1;
    height: 38px;
    padding: 0 12px;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--surface-2);
    font-weight: 600;
  }
  .client {
    padding: 10px 0 4px;
    border-top: 1px solid var(--border);
  }
  .client:first-of-type {
    border-top: 0;
  }
  .offline {
    opacity: 0.5;
  }
  .cname {
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 650;
  }
  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--text-3);
    flex-shrink: 0;
  }
  .dot.on {
    background: #22c55e;
    box-shadow: 0 0 8px #22c55e;
  }
  .edit {
    color: var(--text-3);
    display: grid;
    padding: 4px;
  }
  .edit:hover {
    color: var(--text);
  }
  .vol {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .pct {
    width: 32px;
    text-align: right;
    font-size: 13px;
    color: var(--text-2);
    font-variant-numeric: tabular-nums;
  }
  .muted {
    color: #ef4444 !important;
  }
  .toggle {
    display: flex;
    gap: 8px;
    align-items: center;
    margin-top: 18px;
    color: var(--text-2);
    font-size: 14px;
    cursor: pointer;
  }
  input[type='checkbox'] {
    accent-color: var(--accent);
    width: 18px;
    height: 18px;
  }
</style>
