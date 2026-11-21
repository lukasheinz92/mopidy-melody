from __future__ import annotations

import base64
import json
from pathlib import Path

import httpx
from mopidy.models import Image, Ref
from mutagen.id3 import APIC, ID3
from PIL import Image as PILImage

from mopidy_melody.art import (
    ArtResolver,
    local_uri_to_path,
    normalize,
    similar,
    uri_kind,
)

from .conftest import make_config, make_jpeg, track


def resolver(tmp_path, core, **overrides) -> ArtResolver:
    return ArtResolver(make_config(tmp_path, **overrides), core, tmp_path / "root")


def test_uri_kind():
    assert uri_kind("local:album:md5:abc") == "album"
    assert uri_kind("local:artist:md5:abc") == "artist"
    assert uri_kind("local:track:Mix/a.mp3") == "track"
    assert uri_kind("jellyfin:album:0123abcd") == "album"
    assert uri_kind("m3u:Favs.m3u8") == "playlist"
    assert uri_kind("youtube:video:xyz") == "other"


def test_normalize_and_similar():
    assert normalize("Hráč (Remastered 2011)") == "hrac"
    assert normalize("Demons feat. Someone") == "demons"
    assert similar("Night Visions", "Night Visions (Deluxe)")
    assert not similar("Night Visions", "Evolve")
    assert similar("Living on a prayer", "Livin' On A Prayer")
    assert not similar("Heaven", "Hello")
    assert not similar("", "x")


def test_local_uri_to_path(tmp_path):
    assert (
        local_uri_to_path("local:track:Mix/A%20B.mp3", tmp_path)
        == tmp_path / "Mix/A B.mp3"
    )
    assert local_uri_to_path("youtube:video:x", tmp_path) is None


def test_embedded_id3_art(tmp_path, core, music):
    path = music / "Mix" / "song.mp3"
    path.parent.mkdir()
    path.write_bytes(b"")
    tags = ID3()
    tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="", data=make_jpeg()))
    tags.save(path)

    uri = "local:track:Mix/song.mp3"
    result = resolver(tmp_path, core).get(uri)
    assert result is not None
    with PILImage.open(result) as img:
        assert max(img.size) == 512  # scaled to art_size


def test_folder_art_for_album_and_size_variant(tmp_path, core, music):
    album_dir = music / "Artist" / "Album"
    album_dir.mkdir(parents=True)
    (album_dir / "01.flac").write_bytes(b"not really flac")
    (album_dir / "Folder.JPG").write_bytes(make_jpeg((0, 0, 255)))
    core.library.tracks["local:album:md5:1"] = [
        track("local:track:Artist/Album/01.flac")
    ]

    r = resolver(tmp_path, core)
    small = r.get("local:album:md5:1", size=200)
    assert small is not None and small.name.endswith("-256.jpg")
    with PILImage.open(small) as img:
        assert max(img.size) == 256


def test_backend_data_uri_and_miss_cache(tmp_path, core):
    payload = base64.b64encode(make_jpeg()).decode()
    core.library.images["youtube:video:a"] = [
        Image(uri=f"data:image/jpeg;base64,{payload}")
    ]
    r = resolver(tmp_path, core)
    assert r.get("youtube:video:a") is not None

    assert r.get("youtube:video:missing") is None
    assert list(r.cache_dir.glob("*.none"))
    core.library.images["youtube:video:missing"] = [
        Image(uri=f"data:image/jpeg;base64,{payload}")
    ]
    assert r.get("youtube:video:missing") is None  # still within miss TTL
    assert r.clear() >= 2
    assert r.get("youtube:video:missing") is not None


def test_playlist_uses_first_item_with_art(tmp_path, core):
    payload = base64.b64encode(make_jpeg()).decode()
    core.playlists.items["m3u:Favs.m3u8"] = [
        Ref.track(uri="youtube:video:none", name="x"),
        Ref.track(uri="youtube:video:b", name="y"),
    ]
    core.library.images["youtube:video:b"] = [
        Image(uri=f"data:image/jpeg;base64,{payload}")
    ]
    assert resolver(tmp_path, core).get("m3u:Favs.m3u8") is not None


def _mock_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_deezer_album_match(tmp_path, core):
    core.library.tracks["local:album:md5:2"] = [
        track("local:track:x.mp3", artist="Imagine Dragons", album="Night Visions")
    ]
    jpeg = make_jpeg()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/search/album":
            assert request.url.params["q"] == "Imagine Dragons Night Visions"
            body = {
                "data": [
                    {
                        "title": "Evolve",
                        "artist": {"name": "Imagine Dragons"},
                        "cover_xl": "https://cdn/wrong.jpg",
                    },
                    {
                        "title": "Night Visions (Deluxe)",
                        "artist": {"name": "Imagine Dragons"},
                        "cover_xl": "https://cdn/right.jpg",
                    },
                ]
            }
            return httpx.Response(200, content=json.dumps(body))
        if request.url.path == "/right.jpg":
            return httpx.Response(
                200, content=jpeg, headers={"content-type": "image/jpeg"}
            )
        return httpx.Response(404)

    r = resolver(tmp_path, core, art_local=(), art_web=("deezer",))
    r.client = _mock_client(handler)
    assert r.get("local:album:md5:2") is not None


def test_jellyfin_track_falls_back_to_album(tmp_path, core):
    jpeg = make_jpeg()
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        assert request.headers["X-Emby-Token"] == "tok"
        if request.url.path == "/Items/aaaaaaaa1111/Images/Primary":
            return httpx.Response(404)
        if request.url.path == "/Items/aaaaaaaa1111":
            return httpx.Response(200, content=json.dumps({"AlbumId": "bbbbbbbb2222"}))
        if request.url.path == "/Items/bbbbbbbb2222/Images/Primary":
            return httpx.Response(
                200, content=jpeg, headers={"content-type": "image/jpeg"}
            )
        return httpx.Response(404)

    r = resolver(tmp_path, core, jellyfin_url="http://jf", jellyfin_token="tok")
    r.client = _mock_client(handler)
    assert r.get("jellyfin:track:aaaaaaaa1111") is not None
    assert "/Items/bbbbbbbb2222/Images/Primary" in seen


def test_unknown_source_is_skipped(tmp_path, core):
    r = resolver(tmp_path, core, art_other=("bogus",))
    assert r.get("youtube:video:q") is None


def test_cache_dir_default(tmp_path, core):
    r = resolver(tmp_path, core, art_cache_dir=None)
    assert r.cache_dir == Path(tmp_path / "root" / "art")


def test_split_filename():
    from mopidy_melody.art import split_filename

    assert split_filename("IMAGINE DRAGONS - Demons.mp3") == (
        "IMAGINE DRAGONS",
        "Demons",
    )
    assert split_filename("01 - Queen - Bohemian Rhapsody.flac") == (
        "Queen",
        "Bohemian Rhapsody",
    )
    assert split_filename("Summer of 69 (live).flac") is None


def test_untagged_file_uses_filename_for_web_lookup(tmp_path, core):
    from mopidy.models import Track

    uri = "local:track:Mix/IMAGINE%20DRAGONS%20-%20Demons.mp3"
    core.library.tracks[uri] = [Track(uri=uri, name="IMAGINE DRAGONS - Demons.mp3")]
    jpeg = make_jpeg()
    queries = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/search/track":
            queries.append(request.url.params["q"])
            body = {
                "data": [
                    {
                        "title": "Demons",
                        "artist": {"name": "Imagine Dragons"},
                        "album": {"cover_xl": "https://cdn/demons.jpg"},
                    }
                ]
            }
            return httpx.Response(200, content=json.dumps(body))
        if request.url.path == "/demons.jpg":
            return httpx.Response(
                200, content=jpeg, headers={"content-type": "image/jpeg"}
            )
        return httpx.Response(404)

    r = resolver(tmp_path, core, art_local=(), art_web=("deezer",))
    r.client = _mock_client(handler)
    assert r.get(uri, hints={"title": "IMAGINE DRAGONS - Demons.mp3"}) is not None
    assert queries == ["IMAGINE DRAGONS Demons"]


def test_deezer_quota_error_is_not_cached_as_miss(tmp_path, core):
    core.library.tracks["local:album:md5:3"] = [
        track("local:track:y.mp3", artist="Muse", album="Absolution")
    ]
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        body = {"error": {"type": "Exception", "message": "Quota limit exceeded"}}
        return httpx.Response(200, content=json.dumps(body))

    r = resolver(tmp_path, core, art_local=(), art_web=("deezer",))
    r.client = _mock_client(handler)
    assert r.get("local:album:md5:3") is None
    assert not list(r.cache_dir.glob("*.none"))
    assert r.get("local:album:md5:3") is None
    assert len(calls) == 2  # retried instead of served from the miss cache


def test_candidates_from_deezer_and_musicbrainz(tmp_path, core):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/search/album":
            assert request.url.params["q"] == "Imagine Dragons Evolve"
            body = {
                "data": [
                    {
                        "title": "Evolve",
                        "artist": {"name": "Imagine Dragons"},
                        "cover_xl": "https://cdn/xl.jpg",
                        "cover_medium": "https://cdn/m.jpg",
                    }
                ]
            }
            return httpx.Response(200, content=json.dumps(body))
        if request.url.path == "/ws/2/release-group/":
            body = {
                "release-groups": [
                    {"id": "rg1", "title": "Evolve", "artist-credit": [{"name": "ID"}]}
                ]
            }
            return httpx.Response(200, content=json.dumps(body))
        return httpx.Response(404)

    r = resolver(tmp_path, core)
    r.client = _mock_client(handler)
    found = r.candidates("local:album:1", "album", "Imagine Dragons Evolve")
    assert [(c["source"], c["url"], c["thumb"]) for c in found] == [
        ("Deezer", "https://cdn/xl.jpg", "https://cdn/m.jpg"),
        (
            "MusicBrainz",
            "https://coverartarchive.org/release-group/rg1/front-1200",
            "https://coverartarchive.org/release-group/rg1/front-250",
        ),
    ]
    assert found[0]["subtitle"] == "Imagine Dragons"


def test_override_wins_and_survives_clear(tmp_path, core):
    r = resolver(tmp_path, core)
    assert r.get("youtube:video:x") is None  # cached miss
    r.set_override("youtube:video:x", make_jpeg(), "upload")
    assert r.get("youtube:video:x", 256).name.endswith("-256.jpg")
    r.clear()
    assert r.get("youtube:video:x") is not None
    assert list(r.overrides()["uris"]) == ["youtube:video:x"]
    assert r.remove_override("youtube:video:x")
    assert r.get("youtube:video:x") is None
