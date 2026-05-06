from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from flockr.config.load import ConfigLayer, load_config_layers
from flockr.context import ContextFrame

if TYPE_CHECKING:
    from flockr.runbook.model import Runbook


@dataclass(frozen=True)
class ResolvedRunContext:
    config: dict[str, Any]
    inputs: dict[str, str]
    project: dict[str, str]
    config_layers: tuple[ConfigLayer, ...] = ()

    def to_context_frame(self) -> ContextFrame:
        return ContextFrame(
            {
                "config": self.config,
                "input": self.inputs,
                "project": self.project,
            }
        )


def resolve_run_context(
    runbook: Runbook,
    config_layers: list[ConfigLayer],
    input_overrides: dict[str, str],
    project_dir: str | Path,
) -> ResolvedRunContext:
    project_path = Path(project_dir)
    project = {"dir": str(project_path)}
    config = load_config_layers(config_layers)

    return ResolvedRunContext(
        config=_interpolate_project_dir(config, project["dir"]),
        inputs=_resolve_inputs(runbook, input_overrides, project["dir"]),
        project=project,
        config_layers=tuple(config_layers),
    )


def parse_config_overrides(raw_overrides: list[tuple[str, str]]) -> dict[str, Any]:
    config: dict[str, Any] = {}
    for key, value in raw_overrides:
        _set_deep(config, key.split("."), _parse_override_value(value))
    return config


def _set_deep(config: dict[str, Any], path: list[str], value: Any) -> None:
    current = config
    for part in path[:-1]:
        child = current.setdefault(part, {})
        if not isinstance(child, dict):
            raise ValueError(f"Cannot set nested override through scalar key: {'.'.join(path)}")
        current = child
    current[path[-1]] = value


def _parse_override_value(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _resolve_inputs(runbook: Runbook, input_overrides: dict[str, str], project_dir: str) -> dict[str, str]:
    inputs = dict(runbook.inputs)
    inputs.update(input_overrides)

    return {key: value.replace("${project.dir}", project_dir) for key, value in inputs.items()}


# Can i not jump to tests in intellij?


# Can we review what this does?
def _interpolate_project_dir(value: Any, project_dir: str) -> Any:
    if isinstance(value, dict):
        return {key: _interpolate_project_dir(child, project_dir) for key, child in value.items()}

    if isinstance(value, list):
        return [_interpolate_project_dir(child, project_dir) for child in value]

    if isinstance(value, str):
        return value.replace("${project.dir}", project_dir)

    return value
