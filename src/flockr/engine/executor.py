from __future__ import annotations

import asyncio
import os
import shlex
import uuid
from typing import Protocol

from pydantic import BaseModel

from flockr.logging import command_fields, get_logger
from flockr.runbook import CommandInstance

log = get_logger(__name__)


class CommandResult(BaseModel):
    command: CommandInstance
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""


class Executor(Protocol):
    async def run(self, command: CommandInstance) -> CommandResult:
        pass


class RecordingExecutor:
    def __init__(self) -> None:
        self.commands: list[CommandInstance] = []

    async def run(self, command: CommandInstance) -> CommandResult:
        self.commands.append(command)
        return CommandResult(command=command)


class LocalSubprocessExecutor:
    async def run(self, command: CommandInstance) -> CommandResult:
        if command.context.kind != "local":
            return _unsupported_context(command, "local executor")

        cwd = command.context.values.get("cwd")
        if cwd is not None:
            cwd = os.path.expanduser(cwd)

        log.debug("EXECUTOR", "local.start", **command_fields(command), cwd=cwd)
        result = await _run_process(command, [command.executable, *command.args], cwd=cwd)
        log.debug("EXECUTOR", "local.finish", **command_fields(command), exit_code=result.exit_code)
        return result


class SshSubprocessExecutor:
    async def run(self, command: CommandInstance) -> CommandResult:
        if command.context.kind != "ssh":
            return _unsupported_context(command, "SSH executor")

        remote_command = build_remote_command(command)
        target = _ssh_target(command)

        log.debug("SSH", "ssh.prepare", **command_fields(command), target=target, remote_cmd=remote_command)
        log.debug("SSH", "ssh.start", **command_fields(command), target=target)
        result = await _run_process(command, _ssh_args(command, remote_command))
        log.debug("SSH", "ssh.finish", **command_fields(command), target=target, exit_code=result.exit_code)
        return result


class RoutingExecutor:
    def __init__(self, executors: dict[str, Executor]) -> None:
        self.executors = executors

    async def run(self, command: CommandInstance) -> CommandResult:
        executor = self.executors.get(command.context.kind)
        if executor is None:
            return CommandResult(
                command=command,
                exit_code=1,
                stderr=f"No executor configured for context: {command.context.kind}",
            )

        log.debug("EXECUTOR", "executor.route", **command_fields(command))
        return await executor.run(command)

    async def run_group(self, commands: list[CommandInstance]) -> list[CommandResult]:
        if not commands:
            return []

        executor = self.executors.get(commands[0].context.kind)
        if executor is None:
            return [
                CommandResult(
                    command=command,
                    exit_code=1,
                    stderr=f"No executor configured for context: {command.context.kind}",
                )
                for command in commands
            ]

        run_group = getattr(executor, "run_group", None)
        if run_group is None:
            return [await executor.run(command) for command in commands]

        return await run_group(commands)


def build_remote_command(command: CommandInstance) -> str:
    command_line = shlex.join([command.executable, *command.args])
    cwd = command.context.values.get("cwd")

    if cwd is None:
        return command_line

    return f"cd {shlex.quote(cwd)} && {command_line}"


class StickySshSubprocessExecutor(SshSubprocessExecutor):
    async def run_group(self, commands: list[CommandInstance]) -> list[CommandResult]:
        if not commands:
            return []

        first = commands[0]
        if first.context.kind != "ssh":
            return [_unsupported_context(command, "SSH executor") for command in commands]

        remote_command = build_sticky_remote_command(commands)
        target = _ssh_target(first)

        log.debug("SSH", "ssh.group.prepare", command_count=len(commands), target=target)
        process = await asyncio.create_subprocess_exec(
            *_ssh_args(first, remote_command),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        return split_sticky_results(
            commands,
            stdout.decode(),
            stderr.decode(),
        )


def _unsupported_context(command: CommandInstance, executor_name: str) -> CommandResult:
    return CommandResult(
        command=command,
        exit_code=1,
        stderr=f"Unsupported execution context for {executor_name}: {command.context.kind}",
    )


async def _run_process(command: CommandInstance, argv: list[str], cwd: str | None = None) -> CommandResult:
    process = await asyncio.create_subprocess_exec(
        *argv,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return CommandResult(
        command=command,
        exit_code=process.returncode or 0,
        stdout=stdout.decode(),
        stderr=stderr.decode(),
    )


def _ssh_target(command: CommandInstance) -> str:
    host = command.context.values["host"]
    user = command.context.values.get("user")
    return host if user is None else f"{user}@{host}"


def _ssh_args(command: CommandInstance, remote_command: str) -> list[str]:
    args = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no"]
    port = command.context.values.get("port")
    identity_file = command.context.values.get("identity_file")
    if port is not None:
        args.extend(["-p", port])
    if identity_file is not None:
        args.extend(["-i", os.path.expanduser(identity_file)])
    args.extend([_ssh_target(command), remote_command])
    return args


def build_sticky_remote_command(commands: list[CommandInstance]) -> str:
    token = uuid.uuid4().hex
    lines = ["_flockr_status=0"]
    cwd = commands[0].context.values.get("cwd")
    if cwd is not None:
        lines.append(f"cd {shlex.quote(cwd)} || exit $?")

    for index, command in enumerate(commands):
        command_line = shlex.join([command.executable, *command.args])
        start_marker = f"__FLOCKR_{token}_START_{index}__"
        exit_marker = f"__FLOCKR_{token}_EXIT_{index}__"
        lines.extend(
            [
                f"printf '%s\\n' {shlex.quote(start_marker)}",
                f"printf '%s\\n' {shlex.quote(start_marker)} >&2",
                command_line,
                "_flockr_code=$?",
                'if [ "$_flockr_code" -gt "$_flockr_status" ]; then _flockr_status="$_flockr_code"; fi',
                f"printf '%s:%s\\n' {shlex.quote(exit_marker)} \"$_flockr_code\"",
                f"printf '%s:%s\\n' {shlex.quote(exit_marker)} \"$_flockr_code\" >&2",
            ]
        )
        lines.append('if [ "$_flockr_code" -ne 0 ]; then exit "$_flockr_status"; fi')

    lines.append('exit "$_flockr_status"')
    return "sh -c " + shlex.quote("\n".join(lines))


def split_sticky_results(
    commands: list[CommandInstance],
    stdout: str,
    stderr: str,
) -> list[CommandResult]:
    stdout_parts, stdout_codes = _split_sticky_stream(stdout, len(commands))
    stderr_parts, stderr_codes = _split_sticky_stream(stderr, len(commands))
    results: list[CommandResult] = []

    for index, command in enumerate(commands):
        if index not in stdout_codes and index not in stderr_codes:
            continue
        exit_code = stdout_codes.get(index, stderr_codes.get(index, 1))
        results.append(
            CommandResult(
                command=command,
                exit_code=exit_code,
                stdout=stdout_parts[index],
                stderr=stderr_parts[index],
            )
        )

    return results


def _split_sticky_stream(stream: str, command_count: int) -> tuple[list[str], dict[int, int]]:
    parts = [""] * command_count
    codes: dict[int, int] = {}
    current = 0

    for line in stream.splitlines(keepends=True):
        marker = line.strip()
        if marker.startswith("__FLOCKR_") and "_START_" in marker:
            current = int(marker.rsplit("_START_", 1)[1].removesuffix("__"))
            continue
        if marker.startswith("__FLOCKR_") and "_EXIT_" in marker:
            left, _, raw_code = marker.partition(":")
            index = int(left.rsplit("_EXIT_", 1)[1].removesuffix("__"))
            codes[index] = int(raw_code)
            continue

        parts[current] += line

    return parts, codes
