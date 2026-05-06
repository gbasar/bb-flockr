from __future__ import annotations

from pathlib import Path
from typing import Any

from flockr.config import ConfigSource
from flockr.runbook.model import Command, ExecutionContext, Runbook, Task

_RUNBOOK_METADATA_NODES = {"config", "input", "context", "local", "ssh", "task"}
_TASK_METADATA_NODES = {"context", "local", "ssh", "cwd", "command", "step"}


def load_kdl_runbook(path: str | Path) -> Runbook:
    document = _parse_file(path)
    runbook_node = _one(document.nodes, "runbook")
    return _runbook(runbook_node)


def _parse_file(path: str | Path) -> Any:
    try:
        import ckdl
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "ckdl is required to read KDL files but is not available. "
            "Install Flockr with its runtime dependencies, or use a bundled Flockr artifact."
        ) from exc

    return ckdl.parse(Path(path).read_text(), version="detect")


def _runbook(node: Any) -> Runbook:
    return Runbook(
        name=_first_arg(node, "runbook"),
        config_sources=_config_sources(node.children),
        inputs=_inputs(node.children),
        context=_optional_context(node.children),
        tasks=[_task(child) for child in _task_nodes(node.children)],
    )


def _config_sources(nodes: list[Any]) -> list[ConfigSource]:
    sources: list[ConfigSource] = []

    for node in nodes:
        if node.name != "config":
            continue

        name_or_source = _first_arg(node, "config")
        source = _optional_property(node, "source")
        if source is None:
            sources.append(ConfigSource(location=name_or_source))
        else:
            sources.append(ConfigSource(location=source, name=name_or_source))

    return sources


def _inputs(nodes: list[Any]) -> dict[str, str]:
    inputs: dict[str, str] = {}

    for node in nodes:
        if node.name != "input":
            continue

        name = _first_arg(node, "input")
        default = node.properties.get("default")
        inputs[name] = "" if default is None else str(default)

    return inputs


def _task(node: Any) -> Task:
    return Task(
        name=_node_label(node, "task"),
        for_each=_optional_property(node, "for_each"),
        label=_optional_property(node, "label"),
        if_fail_run=_optional_bool_property(node, "if_fail_run", default=False),
        context=_optional_context(node.children),
        commands=[_command(child) for child in _command_nodes(node.children)],
    )


def _command(node: Any) -> Command:
    exec_node = _optional_one(node.children, "exec")
    run_node = _optional_one(node.children, "run")
    shell_node = _optional_one(node.children, "shell")
    direct_node = run_node or exec_node

    if direct_node is not None:
        executable = _first_arg(direct_node, direct_node.name)
        args = [str(arg) for arg in direct_node.args[1:]]
    elif shell_node is not None:
        executable = "sh"
        args = ["-c", _first_arg(shell_node, "shell")]
    else:
        executable = _first_arg(_one(node.children, "executable"), "executable")
        args_node = _optional_one(node.children, "args")
        args = [] if args_node is None else [str(arg) for arg in args_node.args]

    return Command(
        name=_step_label(node),
        context=_optional_context(node.children),
        executable=executable,
        args=args,
    )


def _optional_context(nodes: list[Any]) -> ExecutionContext | None:
    context_node = _optional_one_of(nodes, ["context", "local", "ssh"])
    cwd = _optional_child_value(nodes, "cwd")
    if context_node is None:
        if cwd is not None:
            return ExecutionContext(kind="local", values={"cwd": cwd})
        return None

    values = {key: str(value) for key, value in context_node.properties.items()}
    for child in context_node.children:
        values[child.name] = str(_first_arg(child, child.name))
    if cwd is not None:
        values["cwd"] = cwd

    return ExecutionContext(kind=_context_kind(context_node), values=values)


def _task_nodes(nodes: list[Any]) -> list[Any]:
    return [node for node in nodes if node.name == "task" or node.name not in _RUNBOOK_METADATA_NODES]


def _command_nodes(nodes: list[Any]) -> list[Any]:
    return [node for node in nodes if node.name in {"command", "step"} or node.name not in _TASK_METADATA_NODES]


def _node_label(node: Any, explicit_name: str) -> str:
    if node.name == explicit_name:
        return _first_arg(node, explicit_name)
    return node.name


def _step_label(node: Any) -> str:
    if node.name in {"command", "step"}:
        return _first_arg(node, node.name)
    return node.name


def _context_kind(node: Any) -> str:
    if node.name == "context":
        return _first_arg(node, "context")
    return node.name


def _one(nodes: list[Any], name: str) -> Any:
    matches = [node for node in nodes if node.name == name]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {name} node, found {len(matches)}")
    return matches[0]


def _optional_one(nodes: list[Any], name: str) -> Any | None:
    matches = [node for node in nodes if node.name == name]
    if len(matches) > 1:
        raise ValueError(f"Expected at most one {name} node, found {len(matches)}")
    return matches[0] if matches else None


def _optional_one_of(nodes: list[Any], names: list[str]) -> Any | None:
    matches = [node for node in nodes if node.name in names]
    if len(matches) > 1:
        joined_names = ", ".join(names)
        raise ValueError(f"Expected at most one context node ({joined_names}), found {len(matches)}")
    return matches[0] if matches else None


def _optional_child_value(nodes: list[Any], name: str) -> str | None:
    node = _optional_one(nodes, name)
    if node is None:
        return None
    return _first_arg(node, name)


def _first_arg(node: Any, node_name: str) -> str:
    if not node.args:
        raise ValueError(f"{node_name} node requires a first argument")
    return str(node.args[0])


def _optional_property(node: Any, name: str) -> str | None:
    value = node.properties.get(name)
    return None if value is None else str(value)


def _optional_bool_property(node: Any, name: str, default: bool) -> bool:
    value = _optional_property(node, name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}
