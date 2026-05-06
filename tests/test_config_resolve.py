from typing import Any

import pytest

from flockr.config import ConfigLayer, ConfigSource, resolve_run_context
from flockr.config.resolve import parse_config_overrides
from flockr.runbook import Runbook


def runbook(name: str = "demo", inputs: dict[str, str] | None = None) -> Runbook:
    return Runbook(name=name, inputs=inputs or {}, tasks=[])


def source(location: str, name: str | None = None) -> ConfigSource:
    return ConfigSource(location=location, name=name)


def source_layer(location: str, name: str | None = None) -> ConfigLayer:
    return ConfigLayer.from_source(source(location, name))


def value_layer(values: dict[str, Any]) -> ConfigLayer:
    return ConfigLayer.from_values(values)


def test_resolve_run_context_loads_config_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "flockr.config.resolve.load_config_layers",
        lambda layers: {"layers": layers, "runtime": {"threads": 1}},
    )

    resolved = resolve_run_context(
        runbook=runbook(),
        config_layers=[source_layer("base.kdl"), source_layer("environment.conf", "envConf")],
        input_overrides={},
        project_dir="/repo",
    )

    assert resolved.config == {
        "layers": [source_layer("base.kdl"), source_layer("environment.conf", "envConf")],
        "runtime": {"threads": 1},
    }
    assert resolved.project == {"dir": "/repo"}
    assert resolved.config_layers == (source_layer("base.kdl"), source_layer("environment.conf", "envConf"))


def test_resolve_run_context_accepts_no_config_sources() -> None:
    resolved = resolve_run_context(
        runbook=runbook(inputs={"host": "nucbox"}),
        config_layers=[],
        input_overrides={},
        project_dir="/repo",
    )

    assert resolved.config == {}
    assert resolved.inputs == {"host": "nucbox"}
    assert resolved.config_layers == ()


def test_resolve_run_context_loads_required_default_sources_before_cli_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "flockr.config.resolve.load_config_layers",
        lambda layers: {"layers": layers},
    )

    resolved = resolve_run_context(
        runbook=runbook(),
        config_layers=[source_layer("default.configs"), source_layer("environment.conf", "envConf")],
        input_overrides={},
        project_dir="/repo",
    )

    assert resolved.config == {
        "layers": [source_layer("default.configs"), source_layer("environment.conf", "envConf")],
    }
    assert resolved.config_layers == (source_layer("default.configs"), source_layer("environment.conf", "envConf"))


def test_resolve_run_context_loads_runbook_config_sources_before_cli_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "flockr.config.resolve.load_config_layers",
        lambda layers: {"layers": layers},
    )
    demo = Runbook(
        name="demo",
        config_sources=[source("runbook.conf", "envConf")],
        tasks=[],
    )

    resolved = resolve_run_context(
        runbook=demo,
        config_layers=[
            source_layer("default.configs"),
            *[ConfigLayer.from_source(config_source) for config_source in demo.config_sources],
            source_layer("cli.conf", "envConf"),
        ],
        input_overrides={},
        project_dir="/repo",
    )

    assert resolved.config == {
        "layers": [
            source_layer("default.configs"),
            source_layer("runbook.conf", "envConf"),
            source_layer("cli.conf", "envConf"),
        ],
    }
    assert resolved.config_layers == (
        source_layer("default.configs"),
        source_layer("runbook.conf", "envConf"),
        source_layer("cli.conf", "envConf"),
    )


def test_resolve_run_context_applies_injected_config_after_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "flockr.config.resolve.load_config_layers",
        lambda _layers: {"runtime": {"threads": 4, "on_failure": "stop"}},
    )

    resolved = resolve_run_context(
        runbook=runbook(),
        config_layers=[source_layer("base.kdl"), value_layer({"runtime": {"threads": 4}})],
        input_overrides={},
        project_dir="/repo",
    )

    assert resolved.config == {"runtime": {"threads": 4, "on_failure": "stop"}}


def test_resolve_run_context_applies_override_file_layers_after_value_layers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_layers: list[ConfigLayer] = []

    def fake_load_config_layers(layers: list[ConfigLayer]) -> dict[str, object]:
        observed_layers.extend(layers)
        return {"runtime": {"threads": 8, "on_failure": "stop"}}

    monkeypatch.setattr(
        "flockr.config.resolve.load_config_layers",
        fake_load_config_layers,
    )

    resolved = resolve_run_context(
        runbook=runbook(),
        config_layers=[
            source_layer("base.kdl"),
            value_layer({"runtime": {"threads": 4}}),
            source_layer("override.kdl"),
        ],
        input_overrides={},
        project_dir="/repo",
    )

    assert resolved.config == {"runtime": {"threads": 8, "on_failure": "stop"}}
    assert observed_layers == [
        source_layer("base.kdl"),
        value_layer({"runtime": {"threads": 4}}),
        source_layer("override.kdl"),
    ]


def test_resolve_run_context_applies_cli_overrides_last() -> None:
    resolved = resolve_run_context(
        runbook=runbook(),
        config_layers=[
            value_layer(
                {
                    "envConf": {
                        "logging": {"level": "info", "format": "json"},
                    }
                }
            ),
            value_layer(
                parse_config_overrides(
                    [
                        ("envConf.logging.level", "debug"),
                        ("envConf.runtime.threads", "4"),
                        ("envConf.runtime.enabled", "true"),
                    ]
                )
            ),
        ],
        input_overrides={},
        project_dir="/repo",
    )

    assert resolved.config == {
        "envConf": {
            "logging": {"level": "debug", "format": "json"},
            "runtime": {"threads": 4, "enabled": True},
        }
    }


def test_resolve_run_context_interpolates_project_dir_in_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "flockr.config.resolve.load_config_layers",
        lambda _layers: {
            "paths": {
                "root": "${project.dir}",
                "items": ["${project.dir}/one"],
            }
        },
    )

    resolved = resolve_run_context(
        runbook=runbook(),
        config_layers=[source_layer("base.kdl")],
        input_overrides={},
        project_dir="/repo",
    )

    assert resolved.config == {
        "paths": {
            "root": "/repo",
            "items": ["/repo/one"],
        }
    }


def test_resolve_run_context_applies_input_overrides_after_runbook_defaults() -> None:
    demo = runbook(
        inputs={"ids": "${project.dir}/ids.txt", "mode": "dry-run"},
    )

    resolved = resolve_run_context(
        runbook=demo,
        config_layers=[],
        input_overrides={"mode": "live"},
        project_dir="/repo",
    )

    assert resolved.inputs == {
        "ids": "/repo/ids.txt",
        "mode": "live",
    }


def test_resolved_run_context_can_create_context_frame() -> None:
    resolved = resolve_run_context(
        runbook=runbook(inputs={"target": "alpha"}),
        config_layers=[],
        input_overrides={},
        project_dir="/repo",
    )

    context = resolved.to_context_frame()

    assert context.get("project.dir") == "/repo"
    assert context.get("input.target") == "alpha"
