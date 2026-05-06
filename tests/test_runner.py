import pytest
from conftest import GroupRecordingExecutor, MappedPolicyExecutor, PolicyRecordingExecutor

from flockr.context import ContextFrame
from flockr.engine import RecordingExecutor, RunEngine, SerialScheduler
from flockr.runbook import Command, ExecutionContext, Runbook, Task


@pytest.mark.asyncio
async def test_run_engine_expands_and_runs_commands_serially() -> None:
    executor = RecordingExecutor()
    engine = RunEngine(SerialScheduler(executor))
    runbook = Runbook(
        name="inspect",
        tasks=[
            Task(
                name="git",
                context=ExecutionContext(kind="local", values={"cwd": "${project.dir}"}),
                commands=[
                    Command(name="status", executable="git", args=["status"]),
                    Command(name="branch", executable="git", args=["branch", "--show-current"]),
                ],
            )
        ],
    )

    result = await engine.run(runbook, ContextFrame({"project": {"dir": "/repo"}}))

    assert [item.command.identity for item in result.results] == ["git.status", "git.branch"]
    assert [command.command_name for command in executor.commands] == ["status", "branch"]


@pytest.mark.asyncio
async def test_run_engine_groups_ssh_commands_with_same_context_by_default() -> None:
    executor = GroupRecordingExecutor()
    engine = RunEngine(SerialScheduler(executor))
    runbook = Runbook(
        name="inspect",
        tasks=[
            Task(
                name="remote",
                context=ExecutionContext(kind="ssh", values={"host": "box-a"}),
                commands=[
                    Command(name="one", executable="one"),
                    Command(name="two", executable="two"),
                ],
            )
        ],
    )

    result = await engine.run(runbook, ContextFrame())

    assert [item.command.identity for item in result.results] == ["remote.one", "remote.two"]
    assert [[command.command_name for command in group] for group in executor.groups] == [["one", "two"]]
    assert executor.commands == []


@pytest.mark.asyncio
async def test_run_engine_does_not_group_sticky_commands_across_tasks() -> None:
    executor = GroupRecordingExecutor()
    engine = RunEngine(SerialScheduler(executor))
    sticky_context = ExecutionContext(kind="ssh", values={"host": "box-a"})
    runbook = Runbook(
        name="inspect",
        tasks=[
            Task(
                name="first",
                context=sticky_context,
                commands=[Command(name="one", executable="one")],
            ),
            Task(
                name="second",
                context=sticky_context,
                commands=[Command(name="two", executable="two")],
            ),
        ],
    )

    result = await engine.run(runbook, ContextFrame())

    assert [item.command.identity for item in result.results] == ["first.one", "second.two"]
    assert executor.groups == []
    assert [command.command_name for command in executor.commands] == ["one", "two"]


@pytest.mark.asyncio
async def test_run_engine_respects_sticky_false_opt_out() -> None:
    executor = GroupRecordingExecutor()
    engine = RunEngine(SerialScheduler(executor))
    runbook = Runbook(
        name="inspect",
        tasks=[
            Task(
                name="remote",
                context=ExecutionContext(kind="ssh", values={"host": "box-a", "sticky": "false"}),
                commands=[
                    Command(name="one", executable="one"),
                    Command(name="two", executable="two"),
                ],
            )
        ],
    )

    result = await engine.run(runbook, ContextFrame())

    assert [item.command.identity for item in result.results] == ["remote.one", "remote.two"]
    assert executor.groups == []
    assert [command.command_name for command in executor.commands] == ["one", "two"]


@pytest.mark.asyncio
async def test_run_engine_stops_after_default_command_failure() -> None:
    executor = PolicyRecordingExecutor([0, 2, 0])
    engine = RunEngine(SerialScheduler(executor))
    runbook = Runbook(
        name="inspect",
        tasks=[
            Task(
                name="local",
                commands=[
                    Command(name="one", executable="one"),
                    Command(name="two", executable="two"),
                    Command(name="three", executable="three"),
                ],
            )
        ],
    )

    result = await engine.run(runbook, ContextFrame())

    assert [item.command.command_name for item in result.results] == ["one", "two"]
    assert [item.exit_code for item in result.results] == [0, 2]


@pytest.mark.asyncio
async def test_failed_loop_item_stops_its_own_steps_but_not_other_items() -> None:
    executor = MappedPolicyExecutor({"local[0].one": 2})
    engine = RunEngine(SerialScheduler(executor, parallel=2))
    runbook = Runbook(
        name="inspect",
        tasks=[
            Task(
                name="local",
                for_each="${items}",
                commands=[
                    Command(name="one", executable="one"),
                    Command(name="two", executable="two"),
                ],
            )
        ],
    )

    result = await engine.run(runbook, ContextFrame({"items": ["a", "b"]}))

    assert sorted(item.command.identity for item in result.results) == [
        "local[0].one",
        "local[1].one",
        "local[1].two",
    ]
    assert sorted(item.exit_code for item in result.results) == [0, 0, 2]
