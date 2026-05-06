from __future__ import annotations

import asyncio
import itertools
from typing import Any, Protocol

from flockr.engine.executor import CommandResult, Executor
from flockr.logging import command_fields, get_logger
from flockr.runbook import CommandInstance

log = get_logger(__name__)


class Scheduler(Protocol):
    async def run_all(self, commands: list[CommandInstance]) -> list[CommandResult]:
        pass


class SerialScheduler:
    def __init__(self, executor: Executor, parallel: int = 2) -> None:
        self.executor = executor
        self.parallel = parallel

    async def run_all(self, commands: list[CommandInstance]) -> list[CommandResult]:
        item_groups = _group_by_item(commands)
        sem = asyncio.Semaphore(self.parallel)

        async def run_item(group: list[CommandInstance]) -> list[CommandResult]:
            async with sem:
                return await self._run_serial(group)

        results_per_item = await asyncio.gather(*[run_item(g) for g in item_groups])
        return [r for results in results_per_item for r in results]

    async def _run_serial(self, commands: list[CommandInstance]) -> list[CommandResult]:
        results: list[CommandResult] = []
        index = 0

        while index < len(commands):
            command = commands[index]
            group = _sticky_group(commands, index)
            if len(group) > 1 and hasattr(self.executor, "run_group"):
                for grouped_command in group:
                    _log_start(grouped_command)
                group_results = await self.executor.run_group(group)  # type: ignore[attr-defined]
                for result in group_results:
                    _log_finish(result)
                results.extend(group_results)
                if group_results and _should_stop(group_results[-1]):
                    break
                if not group_results:
                    break
                index += len(group_results)
                continue

            _log_start(command)
            result = await self.executor.run(command)
            _log_finish(result)
            results.append(result)
            if _should_stop(result):
                break

            index += 1

        return results


def _group_by_item(commands: list[CommandInstance]) -> list[list[CommandInstance]]:
    def key(c: CommandInstance) -> Any:
        return (c.runbook_name, c.task_name, c.task_item)

    return [list(g) for _, g in itertools.groupby(commands, key=key)]


def _log_start(command: CommandInstance) -> None:
    log.debug("SCHEDULER", "command.start", **command_fields(command))


def _log_finish(result: CommandResult) -> None:
    log.debug("SCHEDULER", "command.finish", **command_fields(result.command), exit_code=result.exit_code)


def _sticky_group(commands: list[CommandInstance], start: int) -> list[CommandInstance]:
    first = commands[start]
    if not _is_sticky(first):
        return [first]

    group = [first]
    for command in commands[start + 1:]:
        if command.context != first.context:
            break
        group.append(command)

    return group


def _is_sticky(command: CommandInstance) -> bool:
    value = command.context.values.get("sticky")
    if value is None:
        return command.context.kind == "ssh"
    return value.lower() in {"1", "true", "yes", "on"}


def _should_stop(result: CommandResult) -> bool:
    return result.exit_code != 0
