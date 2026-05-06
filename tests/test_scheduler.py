import asyncio

import pytest
from conftest import GroupRecordingExecutor, MappedPolicyExecutor, ssh_command

from flockr.engine import SerialScheduler
from flockr.runbook import ExecutionContext


@pytest.mark.asyncio
async def test_consecutive_ssh_commands_for_same_item_are_grouped() -> None:
    executor = GroupRecordingExecutor()
    scheduler = SerialScheduler(executor)
    commands = [ssh_command("one"), ssh_command("two")]

    await scheduler.run_all(commands)

    assert [[c.command_name for c in g] for g in executor.groups] == [["one", "two"]]
    assert executor.commands == []


@pytest.mark.asyncio
async def test_ssh_commands_from_different_tasks_are_not_grouped() -> None:
    executor = GroupRecordingExecutor()
    scheduler = SerialScheduler(executor)
    commands = [
        ssh_command("one", task_name="first"),
        ssh_command("two", task_name="second"),
    ]

    await scheduler.run_all(commands)

    assert executor.groups == []
    assert [c.command_name for c in executor.commands] == ["one", "two"]


@pytest.mark.asyncio
async def test_sticky_false_opts_out_of_grouping() -> None:
    executor = GroupRecordingExecutor()
    scheduler = SerialScheduler(executor)
    commands = [
        ssh_command("one"),
        ssh_command("two"),
    ]
    for c in commands:
        object.__setattr__(c, "context", ExecutionContext(kind="ssh", values={"host": "box-a", "sticky": "false"}))

    await scheduler.run_all(commands)

    assert executor.groups == []
    assert [c.command_name for c in executor.commands] == ["one", "two"]


@pytest.mark.asyncio
async def test_parallel_limit_is_respected() -> None:
    concurrent: list[int] = []
    peak: list[int] = [0]
    active = 0

    class TrackingExecutor:
        async def run(self, command):
            nonlocal active
            active += 1
            concurrent.append(active)
            peak[0] = max(peak[0], active)
            await asyncio.sleep(0)
            active -= 1
            from flockr.engine import CommandResult
            return CommandResult(command=command)

    commands = [ssh_command("step", task_name="t", task_item=str(i)) for i in range(6)]
    await SerialScheduler(TrackingExecutor(), parallel=2).run_all(commands)

    assert peak[0] <= 2


@pytest.mark.asyncio
async def test_failure_stops_current_item_steps_only() -> None:
    executor = MappedPolicyExecutor({"remote[a].one": 1})
    scheduler = SerialScheduler(executor, parallel=2)
    commands = [
        ssh_command("one", task_item="a"),
        ssh_command("two", task_item="a"),
        ssh_command("one", task_item="b"),
        ssh_command("two", task_item="b"),
    ]

    results = await scheduler.run_all(commands)

    ran = sorted(r.command.identity for r in results)
    assert ran == ["remote[a].one", "remote[b].one", "remote[b].two"]
