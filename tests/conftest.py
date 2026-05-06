from __future__ import annotations

from flockr.engine import CommandResult
from flockr.runbook import CommandInstance, ExecutionContext


def ssh_command(
    name: str,
    *,
    host: str = "box-a",
    cwd: str | None = None,
    task_name: str = "remote",
    task_item: str | None = None,
    runbook_name: str = "demo",
    executable: str | None = None,
    args: list[str] | None = None,
) -> CommandInstance:
    values: dict[str, str] = {"host": host}
    if cwd is not None:
        values["cwd"] = cwd
    item_label = f"[{task_item}]" if task_item is not None else ""
    return CommandInstance(
        identity=f"{task_name}{item_label}.{name}",
        runbook_name=runbook_name,
        task_name=task_name,
        task_item=task_item,
        command_name=name,
        context=ExecutionContext(kind="ssh", values=values),
        executable=executable or name,
        args=args or [],
    )


def local_command(
    name: str,
    *,
    cwd: str | None = None,
    task_name: str = "local",
    runbook_name: str = "demo",
    executable: str | None = None,
) -> CommandInstance:
    values: dict[str, str] = {}
    if cwd is not None:
        values["cwd"] = cwd
    return CommandInstance(
        identity=f"{task_name}.{name}",
        runbook_name=runbook_name,
        task_name=task_name,
        command_name=name,
        context=ExecutionContext(kind="local", values=values),
        executable=executable or name,
    )


class GroupRecordingExecutor:
    def __init__(self) -> None:
        self.commands: list[CommandInstance] = []
        self.groups: list[list[CommandInstance]] = []

    async def run(self, command: CommandInstance) -> CommandResult:
        self.commands.append(command)
        return CommandResult(command=command)

    async def run_group(self, commands: list[CommandInstance]) -> list[CommandResult]:
        self.groups.append(commands)
        return [CommandResult(command=command) for command in commands]


class PolicyRecordingExecutor:
    """Assigns exit codes in call order. Only reliable for serial execution."""

    def __init__(self, exit_codes: list[int]) -> None:
        self._exit_codes = iter(exit_codes)
        self.commands: list[CommandInstance] = []

    async def run(self, command: CommandInstance) -> CommandResult:
        self.commands.append(command)
        return CommandResult(command=command, exit_code=next(self._exit_codes, 0))


class MappedPolicyExecutor:
    """Assigns exit codes by command identity. Safe for parallel execution."""

    def __init__(self, policy: dict[str, int]) -> None:
        self.policy = policy
        self.commands: list[CommandInstance] = []

    async def run(self, command: CommandInstance) -> CommandResult:
        self.commands.append(command)
        return CommandResult(command=command, exit_code=self.policy.get(command.identity, 0))
