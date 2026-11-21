from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
from mopidy.models import Album, Artist, Image, Ref, Track
from PIL import Image as PILImage


class Future:
    def __init__(self, value: Any) -> None:
        self.value = value

    def get(self, timeout: float | None = None) -> Any:
        return self.value


class FakeLibrary:
    def __init__(self) -> None:
        self.tracks: dict[str, list[Track]] = {}
        self.images: dict[str, list[Image]] = {}
        self.lookups: list[str] = []

    def lookup(self, uris):
        self.lookups.extend(uris)
        return Future({u: self.tracks.get(u, []) for u in uris})

    def get_images(self, uris):
        return Future({u: tuple(self.images.get(u, [])) for u in uris})


class FakePlaylists:
    def __init__(self) -> None:
        self.items: dict[str, list[Ref]] = {}

    def get_items(self, uri):
        return Future(self.items.get(uri))


class FakeCore:
    def __init__(self) -> None:
        self.library = FakeLibrary()
        self.playlists = FakePlaylists()


def make_jpeg(color=(200, 30, 30), size=(800, 800)) -> bytes:
    out = io.BytesIO()
    PILImage.new("RGB", size, color).save(out, "JPEG")
    return out.getvalue()


def make_config(tmp_path: Path, **overrides: Any) -> dict:
    melody = {
        "title": "Melody",
        "album_uris": ("local:directory?type=album",),
        "artist_uris": ("local:directory?type=artist",),
        "art_local": ("embedded", "folder", "backend"),
        "art_jellyfin": ("jellyfin", "backend"),
        "art_other": ("backend",),
        "art_web": (),
        "art_size": 512,
        "art_timeout": 2,
        "art_cache_dir": str(tmp_path / "cache"),
        "jellyfin_url": "",
        "jellyfin_token": "",
        "snapcast_url": "",
    }
    melody.update(overrides)
    return {
        "melody": melody,
        "local": {"media_dir": str(tmp_path / "music")},
        "http": {"port": 6680, "allowed_origins": ()},
    }


@pytest.fixture
def core() -> FakeCore:
    return FakeCore()


@pytest.fixture
def music(tmp_path: Path) -> Path:
    d = tmp_path / "music"
    d.mkdir()
    return d


def track(
    uri: str, name="Song", artist="Artist", album="Album", album_uri=None
) -> Track:
    return Track(
        uri=uri,
        name=name,
        artists=frozenset({Artist(name=artist)}),
        album=Album(
            uri=album_uri, name=album, artists=frozenset({Artist(name=artist)})
        ),
    )
