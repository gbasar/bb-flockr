from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen

from flockr.config.hocon import load_hocon_config_text
from flockr.config.kdl import load_kdl_config_text
from flockr.config.merge import deep_merge

_CONFIG_LOADERS = {
    ".kdl": load_kdl_config_text,
    ".conf": load_hocon_config_text,
    ".hocon": load_hocon_config_text,
}


@dataclass(frozen=True)
class ConfigSource:
    location: str
    name: str | None = None

    @property
    def is_url(self) -> bool:
        return urlparse(self.location).scheme in {"http", "https"}

    @property
    def suffix(self) -> str:
        if self.is_url:
            return PurePosixPath(urlparse(self.location).path).suffix.lower()

        return Path(self.location).suffix.lower()


@dataclass(frozen=True)
class ConfigLayer:
    source: ConfigSource | None = None
    values: dict[str, Any] | None = None

    @classmethod
    def from_source(cls, source: ConfigSource) -> ConfigLayer:
        return cls(source=source)

    @classmethod
    def from_values(cls, values: dict[str, Any]) -> ConfigLayer:
        return cls(values=values)

    def __post_init__(self) -> None:
        if (self.source is None) == (self.values is None):
            raise ValueError("ConfigLayer requires exactly one of source or values")


def load_config_layers(layers: list[ConfigLayer]) -> dict[str, Any]:
    """Load ordered config layers; later nested keys override earlier keys."""
    config: dict[str, Any] = {}
    for layer in layers:
        config = deep_merge(config, _load_config_layer(layer))
    return config


def load_config_file(path: str | Path) -> dict[str, Any]:
    """Load a local config file by extension."""
    return _load_config_source(ConfigSource(location=str(path)))


def _load_config_source(source: ConfigSource) -> dict[str, Any]:
    """Load a config source from disk or HTTP(S) using its file extension."""
    loader = _CONFIG_LOADERS.get(source.suffix)

    if loader is None:
        raise ValueError(f"Unsupported config file extension: {source.location}")

    loaded = loader(_read_source_text(source))
    if source.name is None:
        return loaded
    return {source.name: loaded}


def _read_source_text(source: ConfigSource) -> str:
    if source.is_url:
        return _read_url(source.location)

    return Path(source.location).read_text()


def _read_url(location: str) -> str:
    with urlopen(location, timeout=10) as response:
        return response.read().decode("utf-8")


def _load_config_layer(layer: ConfigLayer) -> dict[str, Any]:
    if layer.source is not None:
        return _load_config_source(layer.source)

    if layer.values is not None:
        return layer.values

    raise ValueError("ConfigLayer requires exactly one of source or values")
