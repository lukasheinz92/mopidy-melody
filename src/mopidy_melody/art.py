"""Cover art resolution with an on-disk cache.

Images are looked up per URI through a chain of sources (see ext.conf), scaled
down once with Pillow and stored as ``<sha1>.jpg``. Misses are remembered for a
day so we don't hammer web services for items that simply have no art.

Covers picked by the user are kept separately (in Mopidy's data dir) as
``<sha1>.jpg`` plus an ``overrides.json`` index; they win over every source and
survive clearing the cache.
"""

from __future__ import annotations

import base64
import difflib
import hashlib
import io
import json
import logging
import os
import re
import threading
import time
import unicodedata
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from . import __version__

if TYPE_CHECKING:
    from mopidy.core import CoreProxy

logger = logging.getLogger(__name__)

USER_AGENT = f"Mopidy-Melody/{__version__} (https://mopidy.com)"
MISS_TTL = 24 * 3600
CORE_TIMEOUT = 15
SIZES = (256, 512)

# Sources whose failures (timeouts, rate limits, 5xx) are worth retrying later.
NETWORK_SOURCES = {"backend", "jellyfin", "deezer", "musicbrainz"}
# Deezer allows 50 requests per 5 seconds per IP; stay below that.
DEEZER_WINDOW = 5.0
DEEZER_MAX = 40

MAX_IMAGE_BYTES = 20 * 1024 * 1024

FOLDER_NAMES = ("cover", "folder", "front", "album", "albumart", "artwork", "art")
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp")


class TransientError(Exception):
    """A lookup failed in a way that may succeed later (don't cache the miss)."""


@dataclass
class Item:
    """What we know about the thing we need art for."""

    uri: str
    kind: str  # album | artist | track | playlist | other
    artist: str | None = None
    album: str | None = None
    title: str | None = None
    mbid: str | None = None  # MusicBrainz release id
    track_uris: list[str] = field(default_factory=list)
    resolved: bool = False


def uri_kind(uri: str) -> str:
    parts = uri.split(":")
    if len(parts) >= 2:
        sub = parts[1].split("?")[0]
        if sub in ("album", "artist", "track", "playlist"):
            return sub
    if parts[0] == "m3u":
        return "playlist"
    return "other"


def normalize(text: str | None) -> str:
    """Lowercase, strip accents, punctuation and bracketed suffixes."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[\(\[].*?[\)\]]", " ", text.lower())
    text = re.sub(r"\b(feat|ft)\..*$", " ", text)
    text = re.sub(r"[^\w]+", " ", text)
    return " ".join(text.split())


def similar(a: str | None, b: str | None) -> bool:
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return False
    if na == nb or na in nb or nb in na:
        return True
    # Small spelling differences ("Living" vs "Livin'") are fine; callers also
    # require the artist to match, which keeps false positives rare.
    return difflib.SequenceMatcher(None, na, nb).ratio() >= 0.88


def split_filename(name: str) -> tuple[str, str] | None:
    """'ARTIST - Title (live).mp3' -> ('ARTIST', 'Title (live)')."""
    name = re.sub(
        r"\.(mp3|flac|ogg|opus|m4a|aac|wav|wma)$", "", name.strip(), flags=re.I
    )
    name = re.sub(r"^\d{1,3}[\s.\-_]+(?=\D)", "", name)  # leading track number
    match = re.match(r"^(.+?)\s+[-\u2013]\s+(.+)$", name)
    if not match:
        return None
    return match.group(1).strip(), match.group(2).strip()


def local_uri_to_path(uri: str, media_dir: Path | None) -> Path | None:
    if uri.startswith("file:"):
        return Path(urllib.parse.unquote(urllib.parse.urlsplit(uri).path))
    if uri.startswith("local:track:") and media_dir:
        rel = urllib.parse.unquote(uri.split(":", 2)[2])
        return media_dir / rel
    return None


def check_image(data: bytes) -> None:
    """Raise ValueError unless ``data`` is an image Pillow can read."""
    from PIL import Image

    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Image is too large")
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
    except Exception as e:
        raise ValueError("Not a supported image") from e


class ArtResolver:
    def __init__(
        self,
        config: Any,
        core: CoreProxy,
        cache_root: Path,
        override_dir: Path | None = None,
    ) -> None:
        cfg = config["melody"]
        self.core = core
        self.size = cfg["art_size"]
        self.timeout = cfg["art_timeout"]
        self.chains = {
            "local": list(cfg["art_local"] or ()),
            "jellyfin": list(cfg["art_jellyfin"] or ()),
            "other": list(cfg["art_other"] or ()),
            "web": list(cfg["art_web"] or ()),
        }
        self.cache_dir = Path(cfg["art_cache_dir"] or cache_root / "art")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.override_dir = override_dir or cache_root / "covers"
        self.override_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.override_dir / "overrides.json"
        self._index_lock = threading.Lock()

        local = config.get("local") or {}
        self.media_dir = Path(local["media_dir"]) if local.get("media_dir") else None

        jellyfin = config.get("jellyfin") or {}
        self.jf_url = (cfg["jellyfin_url"] or jellyfin.get("hostname") or "").rstrip(
            "/"
        )
        self.jf_token = cfg["jellyfin_token"] or jellyfin.get("token") or ""
        self.jf_user = jellyfin.get("user_id") or ""

        http = config.get("http") or {}
        self.http_base = f"http://127.0.0.1:{http.get('port', 6680)}"

        self.executor = ThreadPoolExecutor(
            max_workers=4, thread_name_prefix="melody-art"
        )
        self.client = httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()
        self._mb_lock = threading.Lock()
        self._mb_last = 0.0
        self._dz_lock = threading.Lock()
        self._dz_calls: list[float] = []

    # ------------------------------------------------------------------ cache

    def _key(self, uri: str) -> str:
        return hashlib.sha1(uri.encode()).hexdigest()

    def _lock(self, key: str) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(key, threading.Lock())

    def clear(self) -> int:
        count = 0
        for path in self.cache_dir.iterdir():
            if path.suffix in (".jpg", ".png", ".none"):
                path.unlink(missing_ok=True)
                count += 1
        return count

    def get(
        self, uri: str, size: int | None = None, hints: dict | None = None
    ) -> Path | None:
        """Return the path of a cached image for ``uri`` (resolving it if needed)."""
        key = self._key(uri)
        with self._lock(key):
            master = self.override_dir / f"{key}.jpg"
            if not master.exists():
                master = self.cache_dir / f"{key}.jpg"
            miss = self.cache_dir / f"{key}.none"
            if not master.exists():
                if miss.exists() and time.time() - miss.stat().st_mtime < MISS_TTL:
                    return None
                data, transient = self._resolve(uri, hints or {})
                if data is None:
                    if not transient:
                        miss.touch()
                    return None
                master.write_bytes(self._scale(data, self.size))
                miss.unlink(missing_ok=True)
            if size and size < self.size:
                target = next((s for s in SIZES if s >= size), None)
                if target:
                    variant = self.cache_dir / f"{key}-{target}.jpg"
                    if not variant.exists():
                        variant.write_bytes(self._scale(master.read_bytes(), target))
                    return variant
            return master

    def _scale(self, data: bytes, size: int) -> bytes:
        try:
            from PIL import Image
        except ImportError:
            return data
        try:
            with Image.open(io.BytesIO(data)) as img:
                img = img.convert("RGB")
                img.thumbnail((size, size), Image.Resampling.LANCZOS)
                out = io.BytesIO()
                img.save(out, "JPEG", quality=88, optimize=True, progressive=True)
                return out.getvalue()
        except Exception as e:
            logger.debug("Melody: could not scale image: %s", e)
            return data

    # ------------------------------------------------------------- overrides

    def _read_index(self) -> dict:
        try:
            data = json.loads(self._index_path.read_text("utf-8"))
        except (OSError, ValueError):
            data = {}
        return {"epoch": data.get("epoch", 0), "uris": data.get("uris", {})}

    def _write_index(self, data: dict) -> None:
        data["epoch"] = int(time.time() * 1000)
        tmp = self._index_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1), "utf-8")
        tmp.replace(self._index_path)

    def _drop_cached(self, key: str) -> None:
        for path in self.cache_dir.glob(f"{key}*"):
            if path.suffix in (".jpg", ".png", ".none"):
                path.unlink(missing_ok=True)

    def overrides(self) -> dict:
        """{"epoch": <ms of the last change>, "uris": {uri: {source, time}}}"""
        with self._index_lock:
            return self._read_index()

    def set_override(self, uri: str, data: bytes, source: str) -> None:
        check_image(data)
        key = self._key(uri)
        with self._lock(key):
            target = self.override_dir / f"{key}.jpg"
            target.write_bytes(self._scale(data, self.size))
            self._drop_cached(key)
        with self._index_lock:
            index = self._read_index()
            index["uris"][uri] = {"source": source, "time": int(time.time())}
            self._write_index(index)

    def remove_override(self, uri: str) -> bool:
        key = self._key(uri)
        with self._lock(key):
            path = self.override_dir / f"{key}.jpg"
            existed = path.exists()
            path.unlink(missing_ok=True)
            self._drop_cached(key)
        with self._index_lock:
            index = self._read_index()
            existed = index["uris"].pop(uri, None) is not None or existed
            self._write_index(index)
        return existed

    def fetch_image(self, url: str) -> bytes:
        """Download an image the user picked (a web result or a pasted URL)."""
        scheme = urllib.parse.urlsplit(url).scheme
        if scheme not in ("http", "https", "data") and not url.startswith("/"):
            raise ValueError("Only http(s) image URLs are supported")
        try:
            data = self._fetch(url)
        except (httpx.HTTPError, TransientError, ValueError) as e:
            raise ValueError(f"Could not download the image: {e}") from e
        if not data:
            raise ValueError("The URL did not return an image")
        return data

    def candidates(self, uri: str, kind: str, query: str) -> list[dict]:
        """Images to choose from: what the backend reports, then web hits."""
        found: list[dict] = []

        def add(url, thumb, title, subtitle, source):
            if url and all(c["url"] != url for c in found):
                found.append(
                    {
                        "url": url,
                        "thumb": thumb or url,
                        "title": title or "",
                        "subtitle": subtitle or "",
                        "source": source,
                    }
                )

        try:
            images = self.core.library.get_images([uri]).get(timeout=CORE_TIMEOUT)
            for image in images.get(uri) or ():
                add(image.uri, image.uri, "", "", "Mopidy")
        except Exception as e:
            logger.debug("Melody: get_images failed for %s: %s", uri, e)
        if not query:
            return found

        try:
            if kind == "artist":
                for hit in self._deezer("/search/artist", query)[:12]:
                    pic = hit.get("picture_xl") or ""
                    if "/artist//" not in pic:
                        thumb = hit.get("picture_medium")
                        add(pic, thumb, hit.get("name"), "", "Deezer")
            else:
                for hit in self._deezer("/search/album", query)[:16]:
                    add(
                        hit.get("cover_xl"),
                        hit.get("cover_medium"),
                        hit.get("title"),
                        hit.get("artist", {}).get("name"),
                        "Deezer",
                    )
        except Exception as e:
            logger.debug("Melody: Deezer candidates failed: %s", e)

        if kind != "artist":
            caa = "https://coverartarchive.org/release-group"
            try:
                data = self._mb_get(
                    "https://musicbrainz.org/ws/2/release-group/",
                    {"query": query, "limit": 8},
                )
                for rg in data.get("release-groups", []):
                    credit = rg.get("artist-credit") or [{}]
                    add(
                        f"{caa}/{rg['id']}/front-1200",
                        f"{caa}/{rg['id']}/front-250",
                        rg.get("title"),
                        credit[0].get("name"),
                        "MusicBrainz",
                    )
            except Exception as e:
                logger.debug("Melody: MusicBrainz candidates failed: %s", e)
        return found

    # ------------------------------------------------------------- resolving

    def _resolve(self, uri: str, hints: dict) -> tuple[bytes | None, bool]:
        """Return (image, transient); transient means a source failed and the
        miss shouldn't be cached."""
        scheme = uri.split(":", 1)[0]
        item = Item(
            uri=uri,
            kind=hints.get("kind") or uri_kind(uri),
            artist=hints.get("artist") or None,
            album=hints.get("album") or None,
            title=hints.get("title") or None,
        )
        group = {"local": "local", "file": "local", "jellyfin": "jellyfin"}.get(
            scheme, "other"
        )
        if item.kind == "playlist":
            return self._resolve_playlist(item), False

        transient = False
        for source in self.chains[group] + self.chains["web"]:
            fn = getattr(self, f"_src_{source}", None)
            if fn is None:
                logger.warning("Melody: unknown art source %r", source)
                continue
            try:
                data = fn(item)
            except Exception as e:
                logger.debug("Melody: art source %s failed for %s: %s", source, uri, e)
                transient = transient or source in NETWORK_SOURCES
                data = None
            if data:
                logger.debug("Melody: art for %s from %s", uri, source)
                return data, False
        return None, transient

    def _resolve_playlist(self, item: Item) -> bytes | None:
        refs = self.core.playlists.get_items(item.uri).get(timeout=CORE_TIMEOUT) or []
        for ref in refs[:8]:
            path = self.get(ref.uri)
            if path:
                return path.read_bytes()
        return None

    def _describe(self, item: Item) -> Item:
        """Fill artist/album/track info via library lookup (once, lazily)."""
        if item.resolved:
            return item
        item.resolved = True
        try:
            result = self.core.library.lookup([item.uri]).get(timeout=CORE_TIMEOUT)
        except Exception as e:
            logger.debug("Melody: lookup failed for %s: %s", item.uri, e)
            return item
        tracks = result.get(item.uri) or []
        item.track_uris = [t.uri for t in tracks[:5]]
        if not tracks:
            return item
        track = tracks[0]
        album = track.album
        if item.kind == "artist":
            if not item.artist:
                names = [a.name for t in tracks[:20] for a in t.artists if a.name]
                item.artist = max(set(names), key=names.count) if names else None
            return item
        artists = (album.artists if album and album.artists else None) or track.artists
        if not item.artist:
            item.artist = next((a.name for a in artists if a.name), None)
        if not item.album and album:
            item.album = album.name
        if not item.title:
            item.title = track.name
        if album and album.musicbrainz_id:
            item.mbid = album.musicbrainz_id
        if not item.artist:
            # Untagged files: Mopidy uses the file name, often "Artist - Title.mp3".
            guess = split_filename(item.title or track.name or "")
            if guess:
                item.artist, item.title = guess
        return item

    def _local_files(self, item: Item) -> list[Path]:
        if item.kind == "track" or item.uri.startswith("file:"):
            uris = [item.uri]
        else:
            uris = self._describe(item).track_uris
        paths = [local_uri_to_path(u, self.media_dir) for u in uris]
        return [p for p in paths if p and p.exists()]

    def _fetch(self, url: str, headers: dict | None = None) -> bytes | None:
        if url.startswith("data:"):
            _, _, payload = url.partition(",")
            return base64.b64decode(payload)
        if url.startswith("/"):
            url = self.http_base + url
        resp = self.client.get(url, headers=headers)
        if resp.status_code == 429 or resp.status_code >= 500:
            raise TransientError(f"{url}: HTTP {resp.status_code}")
        if resp.status_code != 200 or not resp.headers.get(
            "content-type", ""
        ).startswith("image"):
            return None
        return resp.content

    # --------------------------------------------------------------- sources

    def _src_embedded(self, item: Item) -> bytes | None:
        if item.kind == "artist":
            return None
        import mutagen

        for path in self._local_files(item)[:3]:
            try:
                audio = mutagen.File(path)
            except mutagen.MutagenError:
                audio = None
            if audio is None:
                # Not recognised as audio (e.g. damaged MPEG frames); a bare
                # ID3 tag may still be readable.
                from mutagen.id3 import ID3

                try:
                    tags = ID3(path)
                except mutagen.MutagenError:
                    continue
            else:
                pictures = getattr(audio, "pictures", None)  # FLAC, Ogg
                if pictures:
                    front = [p for p in pictures if p.type == 3] or pictures
                    return front[0].data
                tags = audio.tags
            if tags is None:
                continue
            if hasattr(tags, "getall"):  # ID3
                apics = tags.getall("APIC")
                if apics:
                    front = [p for p in apics if p.type == 3] or apics
                    return front[0].data
            covr = tags.get("covr") if hasattr(tags, "get") else None  # MP4
            if covr:
                return bytes(covr[0])
            for key in ("metadata_block_picture", "METADATA_BLOCK_PICTURE"):
                if hasattr(tags, "get") and tags.get(key):
                    from mutagen.flac import Picture

                    return Picture(base64.b64decode(tags[key][0])).data
        return None

    def _src_folder(self, item: Item) -> bytes | None:
        files = self._local_files(item)
        if not files:
            return None
        folder = files[0].parent
        candidates = []
        try:
            entries = list(os.scandir(folder))
        except OSError:
            return None
        for entry in entries:
            name, ext = os.path.splitext(entry.name.lower())
            if ext in IMAGE_EXTS and entry.is_file():
                candidates.append((name, entry.path))
        if item.kind == "artist":
            # artist.jpg in the artist folder (one level above the album)
            for parent in (folder, folder.parent):
                for ext in IMAGE_EXTS:
                    p = parent / f"artist{ext}"
                    if p.exists():
                        return p.read_bytes()
            return None
        for preferred in FOLDER_NAMES:
            for name, path in candidates:
                if name == preferred:
                    return Path(path).read_bytes()
        # A single loose image in a non-mixed folder is almost certainly the cover.
        if len(candidates) == 1 and not item.uri.startswith("local:track"):
            return Path(candidates[0][1]).read_bytes()
        return None

    def _src_backend(self, item: Item) -> bytes | None:
        result = self.core.library.get_images([item.uri]).get(timeout=CORE_TIMEOUT)
        images = list(result.get(item.uri) or [])
        if not images:
            return None
        images.sort(key=lambda i: (i.width or 0) * (i.height or 0), reverse=True)
        for image in images:
            data = self._fetch(image.uri)
            if data:
                return data
        return None

    def _src_jellyfin(self, item: Item) -> bytes | None:
        if not self.jf_url or not item.uri.startswith("jellyfin:"):
            return None
        item_id = item.uri.split(":")[-1]
        if not re.fullmatch(r"[0-9a-fA-F-]{8,}", item_id):
            return None
        headers = {"X-Emby-Token": self.jf_token} if self.jf_token else {}
        params = f"?maxWidth={self.size}&quality=90"
        data = self._fetch(
            f"{self.jf_url}/Items/{item_id}/Images/Primary{params}", headers
        )
        if data or item.kind != "track":
            return data
        # Tracks usually have no own image; fall back to their album.
        path = (
            f"/Users/{self.jf_user}/Items/{item_id}"
            if self.jf_user
            else f"/Items/{item_id}"
        )
        resp = self.client.get(self.jf_url + path, headers=headers)
        if resp.status_code != 200:
            return None
        album_id = resp.json().get("AlbumId")
        if not album_id:
            return None
        return self._fetch(
            f"{self.jf_url}/Items/{album_id}/Images/Primary{params}", headers
        )

    def _deezer(self, path: str, query: str) -> list[dict]:
        with self._dz_lock:
            now = time.monotonic()
            self._dz_calls = [t for t in self._dz_calls if now - t < DEEZER_WINDOW]
            if len(self._dz_calls) >= DEEZER_MAX:
                time.sleep(DEEZER_WINDOW - (now - self._dz_calls[0]))
            self._dz_calls.append(time.monotonic())
        resp = self.client.get(f"https://api.deezer.com{path}", params={"q": query})
        if resp.status_code != 200:
            raise TransientError(f"Deezer: HTTP {resp.status_code}")
        data = resp.json()
        if (
            "error" in data
        ):  # e.g. {"error": {"code": 4, "message": "Quota limit exceeded"}}
            raise TransientError(f"Deezer: {data['error']}")
        return data.get("data", [])

    def _src_deezer(self, item: Item) -> bytes | None:
        item = self._describe(item)
        if item.kind == "artist":
            if not item.artist:
                return None
            for hit in self._deezer("/search/artist", item.artist)[:5]:
                pic = hit.get("picture_xl") or ""
                if similar(hit.get("name"), item.artist) and "/artist//" not in pic:
                    return self._fetch(pic)
            return None
        if not item.artist or not (item.album or item.title):
            return None
        if item.album:
            # Plain queries: Deezer's artist:"..." syntax stopped returning hits;
            # results are filtered by similarity below anyway.
            q = f"{item.artist} {item.album}"
            for hit in self._deezer("/search/album", q)[:10]:
                if similar(hit.get("title"), item.album) and similar(
                    hit.get("artist", {}).get("name"), item.artist
                ):
                    return self._fetch(hit["cover_xl"])
        if item.title:
            q = f"{item.artist} {item.title}"
            for hit in self._deezer("/search/track", q)[:10]:
                if similar(hit.get("title"), item.title) and similar(
                    hit.get("artist", {}).get("name"), item.artist
                ):
                    return self._fetch(hit["album"]["cover_xl"])
        return None

    def _mb_get(self, url: str, params: dict) -> dict:
        # MusicBrainz allows one request per second per client.
        with self._mb_lock:
            wait = self._mb_last + 1.1 - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._mb_last = time.monotonic()
            resp = self.client.get(url, params={**params, "fmt": "json"})
        resp.raise_for_status()
        return resp.json()

    def _src_musicbrainz(self, item: Item) -> bytes | None:
        item = self._describe(item)
        if item.kind == "artist":
            return None  # Cover Art Archive has no artist images
        caa = "https://coverartarchive.org"
        if item.mbid:
            data = self._fetch(f"{caa}/release/{item.mbid}/front-500")
            if data:
                return data
        if not item.artist or not item.album:
            return None
        query = f'releasegroup:"{item.album}" AND artist:"{item.artist}"'
        data = self._mb_get(
            "https://musicbrainz.org/ws/2/release-group/", {"query": query, "limit": 5}
        )
        for rg in data.get("release-groups", []):
            if int(rg.get("score", 0)) < 85 or not similar(rg.get("title"), item.album):
                continue
            image = self._fetch(f"{caa}/release-group/{rg['id']}/front-500")
            if image:
                return image
        return None
