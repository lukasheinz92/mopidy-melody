# Mopidy-Melody

A modern, responsive web client for [Mopidy](https://mopidy.com) 4, written from
scratch in the spirit of Mopidy-Mobile (it uses the same JSON-RPC core API calls),
with server-side cover-art resolution and Snapcast multiroom control.

Open it at `http://<mopidy-host>:6680/melody/`.

> **Note:** This is a personal hobby project, built for a self-hosted home setup
> and intended for private, non-commercial use. It is provided as is, without
> warranty or support.

## Features

- **Responsive layout**: sidebar and full player bar (optional queue side panel)
  on desktop; bottom tab bar, mini-player and swipe-down full-screen player on mobile
- **Library**: album and artist grids (Local, Jellyfin, ... as source chips),
  album/artist/playlist pages, a generic browser for every backend (radio,
  YouTube, folders)
- **Browse & Search** (one page): the backends' browse tiles, and a search across all
  backends in parallel above them; results appear as each backend answers.
  Tapping a song plays just that song (the queue is kept); each result also has
  inline play now / play next / add to queue buttons
- **Menu**: Settings → Menu reorders and hides items (shared by all clients, stored
  on the server); on phones the first 4 are tabs and the rest sit under "More"
- **Queue**: drag & drop reordering (mouse and touch), remove, shuffle, clear,
  save as an m3u playlist, repeat/single/random/consume modes
- **Playlists**: create, add tracks to, remove tracks from, delete (m3u)
- **Cover art**: resolved and cached on the server, see [Cover art](#cover-art)
- **Rooms**: Snapcast per-client volume/mute, group mute, stream selection, renaming
- **Themes**: system/light/dark, accent colour, lock-screen controls (Media Session),
  installable as an app (PWA manifest), keyboard shortcuts (space, shift+←/→, `/`)

## Requirements

- Mopidy >= 4.0 (with Mopidy-HTTP enabled), Python >= 3.13
- Optional: Mopidy-Local (local library and [scan](#local-library-scan)),
  Mopidy-Jellyfin, a Snapcast server (Rooms view)

## Installation

```sh
pip install mopidy-melody
# or the latest development version from GitHub
pip install git+https://github.com/lukasheinz92/mopidy-melody
# or from a local checkout
pip install /path/to/mopidy-melody
```

For Docker, `pip install` it the same way in your Mopidy image's `Dockerfile`.
The compiled frontend is committed in `src/mopidy_melody/www`, so the image
needs no Node.js.

## Configuration

```ini
[melody]
enabled = true
title = Melody
album_uris =
    local:directory?type=album
    jellyfin:albums
artist_uris =
    local:directory?type=artist&role=albumartist
    jellyfin:artists
art_local = embedded, folder, backend
art_jellyfin = jellyfin, backend
art_other = backend
art_web = deezer, musicbrainz
art_size = 1024
art_timeout = 8
art_cache_dir =
# Defaults to the [jellyfin] section's hostname/token
jellyfin_url =
jellyfin_token =
# e.g. http://snapserver:1780 - empty hides the Rooms view
snapcast_url =
```

## Cover art

`/melody/api/art?uri=...` resolves images on the server, caches them as scaled
JPEGs (`art_size`, plus 256/512 px variants), and remembers misses for 24 hours.
Sources are tried in order, depending on where the item comes from:

| Item             | Config key     | Default                     |
|------------------|----------------|-----------------------------|
| `local:`/`file:` | `art_local`    | `embedded, folder, backend` |
| `jellyfin:`      | `art_jellyfin` | `jellyfin, backend`         |
| anything else    | `art_other`    | `backend`                   |
| then, for all    | `art_web`      | `deezer, musicbrainz`       |

- `embedded`: pictures in the file's tags (ID3 APIC, FLAC/Ogg pictures, MP4 `covr`)
- `folder`: `cover.*`, `folder.*`, `front.*`, ... next to the file (`artist.*` for artists)
- `backend`: whatever the Mopidy backend reports via `core.library.get_images`
- `jellyfin`: the Jellyfin image API (tracks fall back to their album)
- `deezer`: Deezer search API (albums, tracks and artist photos, no key needed)
- `musicbrainz`: MusicBrainz release-group search + Cover Art Archive (rate-limited to 1 request/s)

Settings → "Cover art cache → Clear" drops the cache.

Wrong or missing cover? "Change cover…" (or "Change picture…" for artists) in a
track's, album's or artist's menu lets you pick a Deezer/MusicBrainz result, paste
an image URL or upload a file. Picked covers win over every source, survive
clearing the cache and can be undone from the same dialog ("Restore automatic").

## Local library scan

With Mopidy-Local enabled, Settings → Library → "Local files" runs
`mopidy local scan` (or `--force` for a full rescan) on the server in the
background at low CPU priority and shows its progress; only one scan runs at a
time. Mopidy-Local reads its database on every query, so no restart is needed.

## Persistent data

Picked covers (`covers/`) and the shared UI preferences (`prefs.json`) are stored
in Mopidy's data dir under `melody/` (in Docker:
`/home/mopidy/.local/share/mopidy/melody`). Mount that directory, or the whole
`/home/mopidy/.local/share/mopidy` (Mopidy-Local's library lives there too),
as a volume so they survive container rebuilds.

## Development

```sh
# Python side
uv venv --python 3.13 && uv pip install -e ".[dev]"
pytest && ruff check src tests

# Frontend (Svelte 5 + Vite), against a running Mopidy with Melody installed
cd frontend
npm install
MOPIDY_URL=http://<mopidy-host>:6680 npm run dev
npm run build        # writes ../src/mopidy_melody/www
```

PyGObject doesn't build on Windows; install Mopidy there with
`uv pip install --no-deps mopidy` plus its other dependencies. The tests never
touch GStreamer.

## License

Apache-2.0
