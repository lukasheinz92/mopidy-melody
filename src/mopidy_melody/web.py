from __future__ import annotations

import json
import logging
import pathlib
import urllib.parse
from typing import TYPE_CHECKING, Any

import tornado.httpclient
import tornado.ioloop
import tornado.web

from . import __version__

if TYPE_CHECKING:
    from mopidy.core import CoreProxy

    from .art import ArtResolver
    from .scan import LocalScanner

logger = logging.getLogger(__name__)

WWW = pathlib.Path(__file__).parent / "www"

# Snapcast JSON-RPC methods the UI may call; everything else is rejected.
SNAPCAST_METHODS = {
    "Server.GetStatus",
    "Client.SetVolume",
    "Client.SetName",
    "Client.SetLatency",
    "Group.SetMute",
    "Group.SetStream",
    "Group.SetClients",
    "Group.SetName",
}


MAX_PREFS_BYTES = 64 * 1024


class Prefs:
    """UI preferences shared by every client (menu order etc.), as one JSON
    object in Mopidy's data dir. The frontend owns the schema."""

    def __init__(self, path: pathlib.Path) -> None:
        self.path = path

    def load(self) -> dict:
        try:
            data = json.loads(self.path.read_text("utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1), "utf-8")
        tmp.replace(self.path)


def make_handlers(
    config: Any,
    core: CoreProxy,
    resolver: ArtResolver,
    prefs: Prefs,
    scanner: LocalScanner | None = None,
) -> list[tuple]:
    cfg = config["melody"]
    http_cfg = config.get("http") or {}
    origins = {o.lower() for o in http_cfg.get("allowed_origins") or ()}
    common = {"origins": origins}
    art = {**common, "resolver": resolver}
    return [
        (r"/api/config", ConfigHandler, {"config": config, "scanner": scanner}),
        (r"/api/prefs", PrefsHandler, {**common, "prefs": prefs}),
        (r"/api/local/scan", LocalScanHandler, {**common, "scanner": scanner}),
        (r"/api/art", ArtHandler, {"resolver": resolver}),
        (r"/api/art/clear", ArtClearHandler, art),
        (r"/api/art/overrides", ArtOverridesHandler, art),
        (r"/api/art/override", ArtOverrideHandler, art),
        (r"/api/art/candidates", ArtCandidatesHandler, art),
        (r"/api/snapcast", SnapcastHandler, {**common, "url": cfg["snapcast_url"]}),
        (r"/(.*)", StaticHandler, {"path": str(WWW), "default_filename": "index.html"}),
    ]


class _ApiHandler(tornado.web.RequestHandler):
    origins: frozenset[str] | set[str] = frozenset()

    def set_default_headers(self) -> None:
        self.set_header("Cache-Control", "no-cache")

    def check_same_origin(self) -> None:
        """Reject cross-site POSTs, mirroring Mopidy's own CSRF protection."""
        origin = self.request.headers.get("Origin")
        if not origin:
            return
        netloc = urllib.parse.urlparse(origin).netloc.lower()
        if netloc != self.request.host.lower() and netloc not in self.origins:
            raise tornado.web.HTTPError(403, "Cross-origin request denied")

    def write_error(self, status_code: int, **kwargs: Any) -> None:
        message = self._reason
        exc = kwargs.get("exc_info", (None, None))[1]
        if isinstance(exc, tornado.web.HTTPError) and exc.log_message:
            message = exc.log_message % exc.args if exc.args else exc.log_message
        self.write_json({"error": message})

    def write_json(self, data: Any) -> None:
        self.set_header("Content-Type", "application/json; charset=utf-8")
        self.write(json.dumps(data))


class ConfigHandler(_ApiHandler):
    def initialize(self, config: Any, scanner: LocalScanner | None) -> None:
        self.config = config
        self.scanner = scanner

    def get(self) -> None:
        cfg = self.config["melody"]
        self.write_json(
            {
                "title": cfg["title"],
                "version": __version__,
                "album_uris": list(cfg["album_uris"] or ()),
                "artist_uris": list(cfg["artist_uris"] or ()),
                "snapcast": bool(cfg["snapcast_url"]),
                "web_art": list(cfg["art_web"] or ()),
                "local_scan": self.scanner is not None,
            }
        )


class LocalScanHandler(_ApiHandler):
    """GET: status of the last/current scan. POST {"full": bool}: start one."""

    def initialize(self, scanner: LocalScanner | None, origins: set[str]) -> None:
        self.scanner = scanner
        self.origins = origins

    def prepare(self) -> None:
        if self.scanner is None:
            raise tornado.web.HTTPError(404, "Mopidy-Local is not enabled")

    def get(self) -> None:
        self.write_json(self.scanner.status())

    def post(self) -> None:
        self.check_same_origin()
        try:
            full = bool(json.loads(self.request.body or b"{}").get("full"))
        except (ValueError, AttributeError) as e:
            raise tornado.web.HTTPError(400, "Invalid JSON") from e
        try:
            started = self.scanner.start(full)
        except OSError as e:
            raise tornado.web.HTTPError(500, "Could not start the scan: %s", e) from e
        if not started:
            raise tornado.web.HTTPError(409, "A scan is already running")
        self.write_json(self.scanner.status())


class ArtHandler(_ApiHandler):
    def initialize(self, resolver: ArtResolver) -> None:
        self.resolver = resolver

    def set_default_headers(self) -> None:
        pass

    async def get(self) -> None:
        uri = self.get_query_argument("uri", "")
        if not uri:
            raise tornado.web.HTTPError(400, "uri is required")
        try:
            size = int(self.get_query_argument("size", "0"))
        except ValueError:
            size = 0
        hints = {
            k: self.get_query_argument(k, None)
            for k in ("kind", "artist", "album", "title")
        }
        loop = tornado.ioloop.IOLoop.current()
        try:
            path = await loop.run_in_executor(
                self.resolver.executor, self.resolver.get, uri, size, hints
            )
        except Exception:
            logger.exception("Melody: resolving art for %s failed", uri)
            path = None
        if path is None:
            self.set_header("Cache-Control", "public, max-age=3600")
            self.set_status(404)
            return
        self.set_header("Content-Type", "image/jpeg")
        self.set_header("Cache-Control", "public, max-age=604800")
        self.write(path.read_bytes())


class ArtClearHandler(_ApiHandler):
    def initialize(self, resolver: ArtResolver, origins: set[str]) -> None:
        self.resolver = resolver
        self.origins = origins

    async def post(self) -> None:
        self.check_same_origin()
        loop = tornado.ioloop.IOLoop.current()
        count = await loop.run_in_executor(self.resolver.executor, self.resolver.clear)
        logger.info("Melody: cleared %d cached art files", count)
        self.write_json({"cleared": count})


class PrefsHandler(_ApiHandler):
    def initialize(self, prefs: Prefs, origins: set[str]) -> None:
        self.prefs = prefs
        self.origins = origins

    def get(self) -> None:
        self.write_json(self.prefs.load())

    def put(self) -> None:
        self.check_same_origin()
        if len(self.request.body) > MAX_PREFS_BYTES:
            raise tornado.web.HTTPError(413, "Preferences too large")
        try:
            data = json.loads(self.request.body)
        except ValueError as e:
            raise tornado.web.HTTPError(400, "Invalid JSON") from e
        if not isinstance(data, dict):
            raise tornado.web.HTTPError(400, "Expected a JSON object")
        self.prefs.save(data)
        self.write_json(data)


class _ArtApiHandler(_ApiHandler):
    def initialize(self, resolver: ArtResolver, origins: set[str]) -> None:
        self.resolver = resolver
        self.origins = origins

    async def run(self, fn, *args) -> Any:
        loop = tornado.ioloop.IOLoop.current()
        return await loop.run_in_executor(self.resolver.executor, fn, *args)

    def required_uri(self) -> str:
        uri = self.get_query_argument("uri", "")
        if not uri:
            raise tornado.web.HTTPError(400, "uri is required")
        return uri


class ArtOverridesHandler(_ArtApiHandler):
    def get(self) -> None:
        self.write_json(self.resolver.overrides())


class ArtOverrideHandler(_ArtApiHandler):
    """POST an image body (upload) or {"url": ...} JSON; DELETE to undo."""

    async def post(self) -> None:
        self.check_same_origin()
        uri = self.required_uri()
        content_type = self.request.headers.get("Content-Type", "")
        try:
            if content_type.startswith("image/"):
                data, source = self.request.body, "upload"
            else:
                try:
                    url = json.loads(self.request.body)["url"]
                except (ValueError, KeyError, TypeError) as e:
                    raise ValueError('Expected an image or {"url": ...}') from e
                data = await self.run(self.resolver.fetch_image, str(url))
                source = str(url) if not str(url).startswith("data:") else "image"
            await self.run(self.resolver.set_override, uri, data, source)
        except ValueError as e:
            raise tornado.web.HTTPError(400, "%s", e) from e
        logger.info("Melody: cover for %s set from %s", uri, source[:200])
        self.write_json(self.resolver.overrides())

    async def delete(self) -> None:
        self.check_same_origin()
        uri = self.required_uri()
        await self.run(self.resolver.remove_override, uri)
        logger.info("Melody: cover override for %s removed", uri)
        self.write_json(self.resolver.overrides())


class ArtCandidatesHandler(_ArtApiHandler):
    async def get(self) -> None:
        uri = self.required_uri()
        kind = self.get_query_argument("kind", "album")
        query = self.get_query_argument("q", "").strip()
        self.write_json(await self.run(self.resolver.candidates, uri, kind, query))


class SnapcastHandler(_ApiHandler):
    def initialize(self, url: str | None, origins: set[str]) -> None:
        self.url = (url or "").rstrip("/")
        self.origins = origins

    async def post(self) -> None:
        self.check_same_origin()
        if not self.url:
            raise tornado.web.HTTPError(404, "Snapcast is not configured")
        try:
            request = json.loads(self.request.body)
        except ValueError as e:
            raise tornado.web.HTTPError(400, "Invalid JSON") from e
        if (
            not isinstance(request, dict)
            or request.get("method") not in SNAPCAST_METHODS
        ):
            raise tornado.web.HTTPError(403, "Method not allowed")
        request.setdefault("jsonrpc", "2.0")
        request.setdefault("id", 1)
        client = tornado.httpclient.AsyncHTTPClient()
        try:
            resp = await client.fetch(
                f"{self.url}/jsonrpc",
                method="POST",
                body=json.dumps(request),
                headers={"Content-Type": "application/json"},
                request_timeout=5,
                raise_error=False,
            )
        except Exception as e:
            logger.warning("Melody: Snapcast request failed: %s", e)
            raise tornado.web.HTTPError(502, "Snapcast unreachable") from e
        if resp.code != 200:
            raise tornado.web.HTTPError(502, f"Snapcast returned {resp.code}")
        self.set_header("Content-Type", "application/json; charset=utf-8")
        self.write(resp.body)


class StaticHandler(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path: str) -> None:
        # Vite emits content-hashed file names under assets/; everything else
        # (index.html, manifest, icons) must be revalidated.
        if path.startswith("assets/"):
            self.set_header("Cache-Control", "public, max-age=31536000, immutable")
        else:
            self.set_header("Cache-Control", "no-cache")
