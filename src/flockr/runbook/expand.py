from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from flockr.context import ContextFrame
from flockr.runbook.model import Command, CommandInstance, ExecutionContext, Runbook, Task

_EXPRESSION = re.compile(r"\$\{([^}]+)}")


def expand_runbook(runbook: Runbook, context: ContextFrame) -> list[CommandInstance]:
    runbook_context = context.child(
        {
            "runbook": {"name": runbook.name},
            "_execution_context": runbook.context or ExecutionContext(kind="local"),
        }
    )
    command_instances: list[CommandInstance] = []

    for task in runbook.tasks:
        command_instances.extend(_expand_task(runbook, task, runbook_context))

    return command_instances


def _expand_task(runbook: Runbook, task: Task, context: ContextFrame) -> list[CommandInstance]:
    task_context = context.child({"task": {"name": task.name}})

    inherited_context = task.context or task_context.get("_execution_context")
    task_context = task_context.child({"_execution_context": inherited_context})

    if task.for_each is None:
        return _expand_task_item(runbook, task, task_context, None)

    collection = _resolve_expression(task.for_each, task_context)
    if not isinstance(collection, Iterable) or isinstance(collection, str):
        raise TypeError(f"for_each must resolve to a collection: {task.for_each}")

    command_instances: list[CommandInstance] = []
    for index, item in enumerate(_collection_items(collection)):
        item_context = task_context.child({"item": item})
        label = _interpolate(task.label, item_context) if task.label is not None else _default_item_label(item, index)
        command_instances.extend(_expand_task_item(runbook, task, item_context, label))

    return command_instances


def _collection_items(collection: Iterable[Any]) -> Iterable[Any]:
    if isinstance(collection, Mapping):
        for key, value in collection.items():
            yield _map_item(str(key), value)
        return

    yield from collection


def _map_item(key: str, value: Any) -> Any:
    if isinstance(value, dict):
        return {**value, "_key": key, "name": key}

    return {"_key": key, "name": key, "value": value}


def _default_item_label(item: Any, index: int) -> str:
    if isinstance(item, dict) and "name" in item:
        return str(item["name"])

    return str(index)


def _expand_task_item(
    runbook: Runbook,
    task: Task,
    context: ContextFrame,
    task_item: str | None,
) -> list[CommandInstance]:
    return [_resolve_command(runbook, task, command, context, task_item) for command in task.commands]


def _resolve_command(
    runbook: Runbook,
    task: Task,
    command: Command,
    context: ContextFrame,
    task_item: str | None,
) -> CommandInstance:
    execution_context = command.context or context.get("_execution_context")
    identity = _command_identity(task.name, task_item, command.name)

    return CommandInstance(
        identity=identity,
        runbook_name=runbook.name,
        task_name=task.name,
        task_item=task_item,
        command_name=command.name,
        context=_resolve_context(execution_context, context),
        executable=_interpolate(command.executable, context),
        args=[_interpolate(arg, context) for arg in command.args],
        if_fail_run=task.if_fail_run,
    )


def _resolve_context(
    execution_context: ExecutionContext,
    context: ContextFrame,
) -> ExecutionContext:
    return ExecutionContext(
        kind=_interpolate(execution_context.kind, context),
        values={key: _interpolate(value, context) for key, value in execution_context.values.items()},
    )


def _resolve_expression(value: str, context: ContextFrame) -> Any:
    match = _EXPRESSION.fullmatch(value)
    if match is None:
        return _interpolate(value, context)

    return context.get(match.group(1))


def _interpolate(value: str, context: ContextFrame) -> str:
    def replace(match: re.Match[str]) -> str:
        resolved = context.get(match.group(1))
        return str(resolved)

    return _EXPRESSION.sub(replace, value)


def _command_identity(task_name: str, task_item: str | None, command_name: str) -> str:
    if task_item is None:
        return f"{task_name}.{command_name}"

    return f"{task_name}[{task_item}].{command_name}"
