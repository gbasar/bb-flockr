from flockr.context import ContextFrame
from flockr.runbook import Command, ExecutionContext, Runbook, Task, expand_runbook


def test_expands_task_over_collection() -> None:
    context = ContextFrame(
        {
            "config": {
                "deploy": {
                    "instances": [
                        {"name": "instance-01", "host": "box-a", "login": "app"},
                        {"name": "instance-02", "host": "box-b", "login": "app"},
                    ]
                },
                "replayer": {"jar_path": "/cache/replayer.jar"},
            },
            "input": {"message_file": "message.dat"},
        }
    )
    runbook = Runbook(
        name="replay",
        tasks=[
            Task(
                name="run",
                for_each="${config.deploy.instances}",
                label="${item.name}",
                commands=[
                    Command(
                        name="run-replayer",
                        context=ExecutionContext(
                            kind="ssh",
                            values={
                                "host": "${item.host}",
                                "user": "${item.login}",
                                "cwd": "/apps/${item.name}",
                            },
                        ),
                        executable="java",
                        args=[
                            "-jar",
                            "${config.replayer.jar_path}",
                            "--file",
                            "${input.message_file}",
                            "--target",
                            "${item.name}",
                        ],
                    )
                ],
            )
        ],
    )

    commands = expand_runbook(runbook, context)

    assert [command.context.values["host"] for command in commands] == ["box-a", "box-b"]
    assert [command.args[-1] for command in commands] == ["instance-01", "instance-02"]
    assert [command.identity for command in commands] == [
        "run[instance-01].run-replayer",
        "run[instance-02].run-replayer",
    ]


def test_command_inherits_task_context() -> None:
    context = ContextFrame({"project": {"dir": "/repo"}})
    runbook = Runbook(
        name="inspect",
        tasks=[
            Task(
                name="git",
                context=ExecutionContext(kind="local", values={"cwd": "${project.dir}"}),
                commands=[Command(name="status", executable="git", args=["status"])],
            )
        ],
    )

    commands = expand_runbook(runbook, context)

    assert commands[0].context == ExecutionContext(kind="local", values={"cwd": "/repo"})


def test_command_defaults_to_local_context() -> None:
    runbook = Runbook(
        name="inspect",
        tasks=[Task(name="task", commands=[Command(name="cmd", executable="echo")])],
    )

    commands = expand_runbook(runbook, ContextFrame())

    assert commands[0].context == ExecutionContext(kind="local")


def test_loop_identity_falls_back_to_index() -> None:
    runbook = Runbook(
        name="inspect",
        tasks=[
            Task(
                name="echo",
                for_each="${items}",
                commands=[Command(name="print", executable="echo", args=["${item}"])],
            )
        ],
    )

    commands = expand_runbook(runbook, ContextFrame({"items": ["a", "b"]}))

    assert [command.identity for command in commands] == ["echo[0].print", "echo[1].print"]


def test_expands_task_over_mapping_with_key_as_default_label() -> None:
    context = ContextFrame(
        {
            "config": {
                "envConf": {
                    "trading": {
                        "shard": {
                            "shard1": {
                                "primary": {
                                    "host": "box-a",
                                    "directory": "/apps/shard_1",
                                }
                            },
                            "shard2": {
                                "primary": {
                                    "host": "box-b",
                                    "directory": "/apps/shard_2",
                                },
                                "name": "config-owned-name",
                            },
                        }
                    }
                }
            }
        }
    )
    runbook = Runbook(
        name="replay",
        tasks=[
            Task(
                name="run",
                for_each="${config.envConf.trading.shard}",
                commands=[
                    Command(
                        name="host",
                        context=ExecutionContext(
                            kind="ssh",
                            values={
                                "host": "${item.primary.host}",
                                "cwd": "${item.primary.directory}",
                            },
                        ),
                        executable="hostname",
                        args=["${item.name}", "${item._key}"],
                    )
                ],
            )
        ],
    )

    commands = expand_runbook(runbook, context)

    assert [command.identity for command in commands] == [
        "run[shard1].host",
        "run[shard2].host",
    ]
    assert [command.context.values["host"] for command in commands] == ["box-a", "box-b"]
    assert [command.context.values["cwd"] for command in commands] == [
        "/apps/shard_1",
        "/apps/shard_2",
    ]
    assert [command.args for command in commands] == [
        ["shard1", "shard1"],
        ["shard2", "shard2"],
    ]


def test_expands_task_over_mapping_with_scalar_values() -> None:
    runbook = Runbook(
        name="inspect",
        tasks=[
            Task(
                name="echo",
                for_each="${ports}",
                commands=[
                    Command(
                        name="print",
                        executable="echo",
                        args=["${item.name}", "${item.value}"],
                    )
                ],
            )
        ],
    )

    commands = expand_runbook(runbook, ContextFrame({"ports": {"jmx": 9001}}))

    assert [command.identity for command in commands] == ["echo[jmx].print"]
    assert commands[0].args == ["jmx", "9001"]


def test_task_if_fail_run_expands_to_command_instance() -> None:
    runbook = Runbook(
        name="inspect",
        tasks=[
            Task(
                name="search",
                if_fail_run=True,
                commands=[
                    Command(
                        name="grep",
                        executable="grep",
                        args=["needle", "file.txt"],
                    )
                ],
            )
        ],
    )

    commands = expand_runbook(runbook, ContextFrame())

    assert commands[0].if_fail_run is True
