from __future__ import annotations

from pathlib import Path
from typing import Any


def load_kdl_config(path: str | Path) -> dict[str, Any]:
    return load_kdl_config_text(Path(path).read_text())


def load_kdl_config_text(text: str) -> dict[str, Any]:
    import ckdl

    document = ckdl.parse(text, version="detect")
    return _children_to_mapping(document.nodes)


def _children_to_mapping(nodes: list[Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}

    for node in nodes:
        value = _node_value(node)
        existing = result.get(node.name)

        if existing is None:
            result[node.name] = value
        elif isinstance(existing, list):
            existing.append(value)
        else:
            result[node.name] = [existing, value]

    return result


def _node_value(node: Any) -> Any:
    properties = dict(node.properties)
    children = list(node.children)
    args = list(node.args)

    if children:
        child_value = _children_to_value(children)
        if properties:
            if isinstance(child_value, dict):
                return {**properties, **child_value}
            return {**properties, "items": child_value}
        return child_value

    if properties:
        if args:
            return {"args": args, **properties}
        return properties

    if len(args) == 1:
        return args[0]

    if args:
        return args

    return {}


def _children_to_value(nodes: list[Any]) -> Any:
    if nodes and all(node.name == "item" for node in nodes):
        return [_node_value(node) for node in nodes]

    return _children_to_mapping(nodes)
