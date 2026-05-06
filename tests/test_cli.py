import pytest

from flockr.cli import _parse_config_source
from flockr.config import ConfigSource


def test_parse_config_source_supports_plain_path() -> None:
    assert _parse_config_source("examples/local-config.kdl") == ConfigSource(location="examples/local-config.kdl")


def test_parse_config_source_supports_named_path() -> None:
    assert _parse_config_source("envConf=examples/environment.conf") == ConfigSource(
        location="examples/environment.conf",
        name="envConf",
    )


@pytest.mark.parametrize("raw_source", ["=examples/environment.conf", "envConf="])
def test_parse_config_source_rejects_incomplete_named_source(raw_source: str) -> None:
    with pytest.raises(ValueError, match="PATH or NAME=PATH"):
        _parse_config_source(raw_source)
