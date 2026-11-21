from __future__ import annotations

import pathlib
from importlib.metadata import version
from typing import TYPE_CHECKING, Any

from mopidy import config, ext

if TYPE_CHECKING:
    from mopidy.core import CoreProxy

__version__ = version("mopidy-melody")

ART_SOURCES = ("embedded", "folder", "backend", "jellyfin", "deezer", "musicbrainz")


class Extension(ext.Extension):
    dist_name = "mopidy-melody"
    ext_name = "melody"
    version = __version__

    def get_default_config(self) -> str:
        return config.read(pathlib.Path(__file__).parent / "ext.conf")

    def get_config_schema(self) -> config.ConfigSchema:
        schema = super().get_config_schema()
        schema["title"] = config.String()
        schema["album_uris"] = config.List(optional=True)
        schema["artist_uris"] = config.List(optional=True)
        for key in ("art_local", "art_jellyfin", "art_other", "art_web"):
            schema[key] = config.List(optional=True)
        schema["art_size"] = config.Integer(minimum=128, maximum=4096)
        schema["art_timeout"] = config.Integer(minimum=1, maximum=60)
        schema["art_cache_dir"] = config.Path(optional=True)
        schema["jellyfin_url"] = config.String(optional=True)
        schema["jellyfin_token"] = config.Secret(optional=True)
        schema["snapcast_url"] = config.String(optional=True)
        return schema

    def setup(self, registry: ext.Registry) -> None:
        registry.add("http:app", {"name": self.ext_name, "factory": factory})


def factory(config: dict[str, Any], core: CoreProxy) -> list[tuple]:
    from .art import ArtResolver
    from .scan import LocalScanner
    from .web import Prefs, make_handlers

    # User choices (covers, menu) live in the data dir so they survive cache
    # clears; mount it as a volume in Docker.
    data_dir = Extension.get_data_dir(config)
    resolver = ArtResolver(
        config, core, Extension.get_cache_dir(config), data_dir / "covers"
    )
    local = config.get("local") or {}
    scanner = LocalScanner() if local.get("enabled") else None
    return make_handlers(
        config, core, resolver, Prefs(data_dir / "prefs.json"), scanner
    )
