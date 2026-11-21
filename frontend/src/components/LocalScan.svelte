<script>
  // Settings row: run `mopidy local scan` on the server and follow its progress.
  import Icon from './Icon.svelte';
  import { getScanStatus, startScan } from '../lib/api.js';
  import { invalidate } from '../lib/library.js';
  import { confirm } from '../lib/ui.svelte.js';
  import { toast, toastError } from '../lib/toast.svelte.js';

  let status = $state(null);
  let showLog = $state(false);
  let timer;

  const running = $derived(status?.state === 'running');
  const percent = $derived(
    status?.total ? Math.min(100, Math.round((status.scanned / status.total) * 100)) : null
  );

  async function poll() {
    clearTimeout(timer);
    try {
      const wasRunning = status?.state === 'running';
      status = await getScanStatus();
      if (status.state === 'running') timer = setTimeout(poll, 2000);
      else if (wasRunning) finished();
    } catch (e) {
      timer = setTimeout(poll, 5000);
    }
  }

  function finished() {
    invalidate(); // new albums/artists should show up right away
    if (status.state === 'done') toast(`Scan finished: ${summary(status)}`);
    else toast('Scan failed, see the log', { error: true });
  }

  async function scan(full) {
    if (
      full &&
      !(await confirm({
        title: 'Full rescan?',
        message: 'Re-reads the tags of every file, not only new or changed ones. This takes longer.',
        confirmLabel: 'Rescan',
      }))
    )
      return;
    try {
      status = await startScan(full);
      showLog = false;
      timer = setTimeout(poll, 1000);
    } catch (e) {
      toastError(e, 'Could not start the scan');
      poll();
    }
  }

  function summary(s) {
    const parts = [];
    if (s.files != null) parts.push(`${s.files} files`);
    parts.push(`${s.scanned || 0} scanned`);
    if (s.removed) parts.push(`${s.removed} removed`);
    if (s.warnings) parts.push(`${s.warnings} warnings`);
    return parts.join(', ');
  }

  const ago = (t) => new Date(t * 1000).toLocaleString();

  function took(s) {
    const sec = Math.round(s.finished - s.started);
    return sec < 60 ? `${sec} s` : `${Math.floor(sec / 60)} min ${sec % 60} s`;
  }

  $effect(() => {
    poll();
    return () => clearTimeout(timer);
  });
</script>

<div class="row">
  <div class="label">
    Local files
    <div class="hint">
      {#if running}
        {#if status.total == null}
          Looking for files…
        {:else}
          Scanned {status.scanned} of {status.total}{status.files != null ? ` (${status.files} files in total)` : ''}
        {/if}
      {:else if status?.state === 'done'}
        Last scan {ago(status.finished)}: {summary(status)}, took {took(status)}
      {:else if status?.state === 'failed'}
        Last scan failed (exit code {status.exit_code})
      {:else}
        Scan the music folder for new, changed and removed files
      {/if}
    </div>
  </div>
  <div class="buttons">
    <button class="btn" onclick={() => scan(false)} disabled={running}>
      {#if running}<span class="spin"></span>{:else}<Icon name="refresh" size={18} />{/if} Scan
    </button>
    <button class="btn" onclick={() => scan(true)} disabled={running}>Full rescan</button>
  </div>
  {#if running}
    <div class="bar" class:indeterminate={percent == null}>
      <div style:width="{percent ?? 30}%"></div>
    </div>
  {/if}
  {#if status?.tail?.length && !running}
    <button class="log-toggle" onclick={() => (showLog = !showLog)}>
      {showLog ? 'Hide' : 'Show'} log
    </button>
    {#if showLog}<pre class="log">{status.tail.join('\n')}</pre>{/if}
  {/if}
</div>

<style>
  .row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 14px 0;
    border-top: 1px solid var(--border);
    flex-wrap: wrap;
  }
  .label {
    font-weight: 600;
  }
  .hint {
    font-size: 13px;
    color: var(--text-3);
    font-weight: 400;
    margin-top: 2px;
  }
  .buttons {
    display: flex;
    gap: 8px;
  }
  .btn:disabled {
    opacity: 0.5;
  }
  .spin {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    border: 2px solid var(--surface);
    border-top-color: var(--accent);
    animation: spin 0.8s linear infinite;
  }
  .bar {
    flex-basis: 100%;
    height: 6px;
    border-radius: 3px;
    background: var(--surface-2);
    overflow: hidden;
  }
  .bar div {
    height: 100%;
    background: var(--accent);
    border-radius: 3px;
    transition: width 0.4s;
  }
  .bar.indeterminate div {
    animation: slide 1.2s ease-in-out infinite;
  }
  @keyframes slide {
    from {
      transform: translateX(-100%);
    }
    to {
      transform: translateX(350%);
    }
  }
  .log-toggle {
    flex-basis: 100%;
    text-align: left;
    font-size: 13px;
    color: var(--accent-text);
    margin-top: -6px;
  }
  .log {
    flex-basis: 100%;
    max-height: 260px;
    overflow: auto;
    margin: 0;
    padding: 10px;
    border-radius: var(--radius-sm);
    background: var(--surface-2);
    font-size: 12px;
    white-space: pre-wrap;
    word-break: break-word;
  }
</style>
