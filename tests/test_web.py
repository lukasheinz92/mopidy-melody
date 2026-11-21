from __future__ import annotations

import base64
import json

import tornado.web
from mopidy.models import Image
from tornado.testing import AsyncHTTPTestCase

from mopidy_melody.art import ArtResolver
from mopidy_melody.web import Prefs, make_handlers

from .conftest import FakeCore, make_config, make_jpeg


class WebTest(AsyncHTTPTestCase):
    snapcast_url = ""

    def get_app(self):
        import tempfile
        from pathlib import Path

        self.tmp = Path(tempfile.mkdtemp())
        self.core = FakeCore()
        config = make_config(self.tmp, snapcast_url=self.snapcast_url)
        self.resolver = ArtResolver(config, self.core, self.tmp / "root")
        prefs = Prefs(self.tmp / "data" / "prefs.json")
        return tornado.web.Application(
            make_handlers(config, self.core, self.resolver, prefs)
        )

    def test_config(self):
        resp = self.fetch("/api/config")
        assert resp.code == 200
        data = json.loads(resp.body)
        assert data["title"] == "Melody"
        assert data["snapcast"] is False
        assert data["album_uris"] == ["local:directory?type=album"]
        assert data["local_scan"] is False

    def test_local_scan_disabled(self):
        assert self.fetch("/api/local/scan").code == 404
        assert self.fetch("/api/local/scan", method="POST", body="{}").code == 404

    def test_art_hit_and_miss(self):
        payload = base64.b64encode(make_jpeg()).decode()
        self.core.library.images["youtube:video:a"] = [
            Image(uri=f"data:image/jpeg;base64,{payload}")
        ]
        resp = self.fetch("/api/art?uri=youtube:video:a&size=256")
        assert resp.code == 200
        assert resp.headers["Content-Type"] == "image/jpeg"
        assert "max-age=604800" in resp.headers["Cache-Control"]
        assert self.fetch("/api/art?uri=youtube:video:none").code == 404
        assert self.fetch("/api/art").code == 400

    def test_art_clear_rejects_cross_origin(self):
        resp = self.fetch(
            "/api/art/clear",
            method="POST",
            body="",
            headers={"Origin": "http://evil.example"},
        )
        assert resp.code == 403
        resp = self.fetch("/api/art/clear", method="POST", body="")
        assert resp.code == 200

    def test_snapcast_disabled(self):
        body = json.dumps({"method": "Server.GetStatus"})
        assert self.fetch("/api/snapcast", method="POST", body=body).code == 404

    def test_prefs_roundtrip(self):
        assert json.loads(self.fetch("/api/prefs").body) == {}
        prefs = {"nav": {"order": ["browse", "search"], "hidden": ["rooms"]}}
        resp = self.fetch("/api/prefs", method="PUT", body=json.dumps(prefs))
        assert resp.code == 200
        assert json.loads(self.fetch("/api/prefs").body) == prefs
        assert self.fetch("/api/prefs", method="PUT", body="[1]").code == 400
        resp = self.fetch(
            "/api/prefs",
            method="PUT",
            body="{}",
            headers={"Origin": "http://evil.example"},
        )
        assert resp.code == 403

    def test_cover_override_upload_and_undo(self):
        payload = base64.b64encode(make_jpeg((0, 0, 200))).decode()
        self.core.library.images["youtube:video:a"] = [
            Image(uri=f"data:image/jpeg;base64,{payload}")
        ]
        original = self.fetch("/api/art?uri=youtube:video:a").body

        resp = self.fetch(
            "/api/art/override?uri=youtube:video:a",
            method="POST",
            body=make_jpeg((0, 200, 0)),
            headers={"Content-Type": "image/jpeg"},
        )
        assert resp.code == 200
        index = json.loads(resp.body)
        assert index["uris"]["youtube:video:a"]["source"] == "upload"
        assert index["epoch"] > 0
        overridden = self.fetch("/api/art?uri=youtube:video:a&size=256").body
        assert overridden != original

        # Survives clearing the cache.
        self.fetch("/api/art/clear", method="POST", body="")
        assert self.fetch("/api/art?uri=youtube:video:a").body != original

        resp = self.fetch("/api/art/override?uri=youtube:video:a", method="DELETE")
        assert json.loads(resp.body)["uris"] == {}
        assert self.fetch("/api/art?uri=youtube:video:a").body == original

    def test_cover_override_from_url_and_errors(self):
        payload = base64.b64encode(make_jpeg()).decode()
        body = json.dumps({"url": f"data:image/jpeg;base64,{payload}"})
        resp = self.fetch("/api/art/override?uri=x:album:1", method="POST", body=body)
        assert resp.code == 200
        assert self.fetch("/api/art?uri=x:album:1").code == 200

        bad = json.dumps({"url": "file:///etc/passwd"})
        resp = self.fetch("/api/art/override?uri=x:album:1", method="POST", body=bad)
        assert resp.code == 400
        assert "http" in json.loads(resp.body)["error"]
        resp = self.fetch(
            "/api/art/override?uri=x:album:1",
            method="POST",
            body=b"not an image",
            headers={"Content-Type": "image/png"},
        )
        assert resp.code == 400
        assert self.fetch("/api/art/override", method="POST", body="{}").code == 400

    def test_candidates_include_backend_images(self):
        self.core.library.images["youtube:video:a"] = [Image(uri="/yt/a.jpg")]
        resp = self.fetch("/api/art/candidates?uri=youtube:video:a&kind=album")
        assert json.loads(resp.body) == [
            {
                "url": "/yt/a.jpg",
                "thumb": "/yt/a.jpg",
                "title": "",
                "subtitle": "",
                "source": "Mopidy",
            }
        ]

    def test_static_index(self):
        resp = self.fetch("/")
        assert resp.code == 200
        assert resp.headers["Cache-Control"] == "no-cache"


class SnapcastProxyTest(WebTest):
    snapcast_url = "http://127.0.0.1:1"

    def test_method_whitelist(self):
        body = json.dumps({"method": "Server.DeleteClient", "params": {"id": "x"}})
        assert self.fetch("/api/snapcast", method="POST", body=body).code == 403

    def test_unreachable(self):
        body = json.dumps({"method": "Server.GetStatus"})
        assert self.fetch("/api/snapcast", method="POST", body=body).code == 502

    def test_config(self):
        assert json.loads(self.fetch("/api/config").body)["snapcast"] is True

    def test_snapcast_disabled(self):
        pass
