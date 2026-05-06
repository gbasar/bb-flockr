import pytest

import flockr.config.load as config_load
from flockr.config import (
    ConfigLayer,
    ConfigSource,
    load_config_file,
    load_config_layers,
)

WORK_CONFIG = {
    "runtime": {"javaHome": "/usr/java/latest"},
    "logging": {"level": "info"},
}


def test_config_source_suffix_supports_urls() -> None:
    source = ConfigSource(location="http://config-web/environment.conf?version=1")

    assert source.is_url
    assert source.suffix == ".conf"


def test_load_config_file_uses_hocon_for_conf_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    config_file = tmp_path / "environment.conf"
    config_file.write_text("runtime.javaHome = /usr/java/latest")
    monkeypatch.setitem(
        config_load._CONFIG_LOADERS,
        ".conf",
        lambda _text: WORK_CONFIG,
    )

    assert load_config_file(config_file) == WORK_CONFIG


def test_named_config_source_wraps_loaded_file_to_avoid_collisions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    config_file = tmp_path / "environment.conf"
    config_file.write_text("runtime.javaHome = /usr/java/latest")
    monkeypatch.setitem(
        config_load._CONFIG_LOADERS,
        ".conf",
        lambda _text: WORK_CONFIG,
    )

    assert load_config_layers([ConfigLayer.from_source(ConfigSource(location=str(config_file), name="envConf"))]) == {
        "envConf": WORK_CONFIG
    }


def test_config_sources_merge_nested_keys(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    base = tmp_path / "base.kdl"
    override = tmp_path / "override.kdl"
    base.write_text("base")
    override.write_text("override")
    monkeypatch.setitem(
        config_load._CONFIG_LOADERS,
        ".kdl",
        lambda text: {
            "base": {"envConf": {"logging": {"level": "info"}, "runtime": {"threads": 1}}},
            "override": {"envConf": {"logging": {"level": "debug"}}},
        }[text],
    )

    assert load_config_layers(
        [
            ConfigLayer.from_source(ConfigSource(location=str(base))),
            ConfigLayer.from_source(ConfigSource(location=str(override))),
        ]
    ) == {
        "envConf": {
            "logging": {"level": "debug"},
            "runtime": {"threads": 1},
        }
    }


def test_config_layers_merge_sources_and_values_in_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    base = tmp_path / "base.kdl"
    base.write_text("base")
    monkeypatch.setitem(
        config_load._CONFIG_LOADERS,
        ".kdl",
        lambda _text: {"runtime": {"threads": 1, "on_failure": "stop"}},
    )

    assert load_config_layers(
        [
            ConfigLayer.from_source(ConfigSource(location=str(base))),
            ConfigLayer.from_values({"runtime": {"threads": 4}}),
        ]
    ) == {"runtime": {"threads": 4, "on_failure": "stop"}}


def test_config_layer_rejects_missing_or_ambiguous_payload() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        ConfigLayer()
    with pytest.raises(ValueError, match="exactly one"):
        ConfigLayer(
            source=ConfigSource(location="base.kdl"),
            values={},
        )


def test_url_config_source_uses_fetched_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ConfigSource(location="http://config-web/environment.conf", name="envConf")
    monkeypatch.setattr(
        config_load,
        "_read_url",
        lambda location: f"fetched from {location}",
    )
    monkeypatch.setitem(
        config_load._CONFIG_LOADERS,
        ".conf",
        lambda text: {"source": text},
    )

    assert load_config_layers([ConfigLayer.from_source(source)]) == {
        "envConf": {
            "source": "fetched from http://config-web/environment.conf",
        }
    }
