from pathlib import Path

import pytest

from flockr.config import ConfigLayer, ConfigSource, resolve_run_context
from flockr.context import ContextFrame
from flockr.runbook import CommandInstance, expand_runbook, load_kdl_runbook


def _resolve_example(kdl_path: str) -> list[CommandInstance]:
    runbook = load_kdl_runbook(Path(kdl_path))
    resolved = resolve_run_context(
        runbook=runbook,
        config_layers=[ConfigLayer.from_source(s) for s in runbook.config_sources],
        input_overrides={},
        project_dir="/repo",
    )
    return expand_runbook(runbook, resolved.to_context_frame())


@pytest.fixture(scope="module")
def blackbird_replay() -> list[CommandInstance]:
    return _resolve_example("examples/blackbird-replay.kdl")


def test_local_example_uses_named_env_config() -> None:
    runbook = load_kdl_runbook(Path("examples/local-runbook.kdl"))
    resolved = resolve_run_context(
        runbook=runbook,
        config_layers=[ConfigLayer.from_source(ConfigSource(location="examples/local-config.kdl", name="envConf"))],
        input_overrides={},
        project_dir="/repo",
    )

    commands = expand_runbook(
        runbook,
        resolved.to_context_frame().child({"input": {"replay_id_file": "ids.txt"}}),
    )

    assert [command.identity for command in commands] == [
        "inspect[alpha].print-instance",
        "inspect[beta].print-instance",
    ]
    assert [command.context.values["cwd"] for command in commands] == ["/repo", "/repo"]


def test_ssh_smoke_example_uses_input_host() -> None:
    runbook = load_kdl_runbook(Path("examples/ssh-smoke.kdl"))

    commands = expand_runbook(runbook, ContextFrame({"input": {"host": "work-alias"}}))

    assert [command.command_name for command in commands] == ["whoami", "hostname", "pwd"]
    assert {command.context.kind for command in commands} == {"ssh"}
    assert {command.context.values["host"] for command in commands} == {"work-alias"}
    assert all("user" not in command.context.values for command in commands)


def test_blackbird_replay_expands_one_step_per_shard_per_task(blackbird_replay: list[CommandInstance]) -> None:
    assert [c.identity for c in blackbird_replay] == [
        "Prepare local replay inputs.Check order id file",
        "Prepare local replay inputs.Show target environment",
        "Replay trade messages[shard11].Upload order id file",
        "Replay trade messages[shard11].Unpack archive",
        "Replay trade messages[shard11].Copy trading logs",
        "Replay trade messages[shard11].Repair copied log",
        "Replay trade messages[shard11].Replay selected orders",
        "Replay trade messages[shard12].Upload order id file",
        "Replay trade messages[shard12].Unpack archive",
        "Replay trade messages[shard12].Copy trading logs",
        "Replay trade messages[shard12].Repair copied log",
        "Replay trade messages[shard12].Replay selected orders",
        "Replay trade messages[shard13].Upload order id file",
        "Replay trade messages[shard13].Unpack archive",
        "Replay trade messages[shard13].Copy trading logs",
        "Replay trade messages[shard13].Repair copied log",
        "Replay trade messages[shard13].Replay selected orders",
        "Replay trade messages[shard21].Upload order id file",
        "Replay trade messages[shard21].Unpack archive",
        "Replay trade messages[shard21].Copy trading logs",
        "Replay trade messages[shard21].Repair copied log",
        "Replay trade messages[shard21].Replay selected orders",
    ]


def test_blackbird_replay_preflight_steps_run_locally(blackbird_replay: list[CommandInstance]) -> None:
    assert [c.context.kind for c in blackbird_replay[:2]] == ["local", "local"]
    assert blackbird_replay[0].executable == "test"
    assert blackbird_replay[0].args == ["-s", "orders-to-replay.txt"]


def test_blackbird_replay_scp_upload_targets_correct_host_and_path(blackbird_replay: list[CommandInstance]) -> None:
    scp = blackbird_replay[2]

    assert scp.executable == "scp"
    assert scp.args == [
        "orders-to-replay.txt",
        "sysusetprd@bb-host-a.example.com:/appBaseDir/shard1/trading/replay-order-ids.txt",
    ]


def test_blackbird_replay_tar_step_unpacks_dated_archive(blackbird_replay: list[CommandInstance]) -> None:
    tar = blackbird_replay[3]

    assert tar.context.values == {
        "host": "bb-host-a.example.com",
        "user": "sysusetprd",
        "cwd": "/appBaseDir/shard1/trading",
    }
    assert tar.executable == "tar"
    assert tar.args == ["-xzf", "data/trading/archive/trading-shard11-20260430.00.00.00.123.tar.gz", "-C", "."]


def test_blackbird_replay_republisher_step_includes_required_java_args(blackbird_replay: list[CommandInstance]) -> None:
    republish = blackbird_replay[6]

    assert republish.executable == "sh"
    shell_cmd = republish.args[1]
    assert "com.barclays.eq.apex.tools.TxnLogRepublisher" in shell_cmd
    assert 'java -cp "app/trading/lib/trading-345.2.1.jar"' in shell_cmd
    assert '--host="eqht-nyk-prd-sol"' in shell_cmd
    assert '--vpn="eqht_nyk_prd"' in shell_cmd
    assert "trading.data-timestamp.log" in shell_cmd
    assert "replay-order-ids.txt" in shell_cmd


def test_blackbird_replay_second_host_shards_target_correct_host(blackbird_replay: list[CommandInstance]) -> None:
    assert blackbird_replay[18].context.values["host"] == "bb-host-b.example.com"


def test_blackbird_trace_recovery_example_uses_selected_shard() -> None:
    commands = _resolve_example("examples/blackbird-trace-recovery.kdl")

    assert [command.identity for command in commands] == [
        "Trace startup recovery[shard11].Clone app root",
        "Trace startup recovery[shard11].Seed inbound log",
        "Trace startup recovery[shard11].Enable trace logging",
        "Trace startup recovery[shard11].Start Blackbird",
    ]
    assert {command.context.kind for command in commands} == {"ssh"}
    assert commands[0].context.values == {
        "host": "bb-host-a.example.com",
        "user": "sysusetprd",
        "cwd": "/tmp/blackbird-trace/shard11",
    }
    assert commands[1].executable == "cp"
    assert commands[1].args == [
        "data/trading/archive/trading-shard11-20260430.00.00.00.123.in.log",
        "log/trading/trading.data-timestamp.in.log",
    ]
    assert "log.level=TRACE" in commands[2].args[1]
    assert "app/trading/bin/start.sh" in commands[3].args[1]


def test_blackbird_debug_recovery_example_starts_suspended() -> None:
    commands = _resolve_example("examples/blackbird-debug-recovery.kdl")

    assert [command.identity for command in commands] == [
        "Debug startup recovery[shard11].Clone app root",
        "Debug startup recovery[shard11].Seed inbound log",
        "Debug startup recovery[shard11].Enable debug config",
        "Debug startup recovery[shard11].Start Blackbird suspended",
    ]
    assert {command.context.kind for command in commands} == {"ssh"}
    assert commands[0].context.values == {
        "host": "bb-host-a.example.com",
        "user": "sysusetprd",
        "cwd": "/tmp/blackbird-trace/shard11",
    }
    assert "log.level=DEBUG" in commands[2].args[1]
    assert "suspend=y" in commands[3].args[1]
    assert "address=*:5005" in commands[3].args[1]
    assert "app/trading/bin/start.sh" in commands[3].args[1]


def test_e2e_debug_runbook_expands_over_selected_shards() -> None:
    runbook = load_kdl_runbook(Path("tests/e2e/debug-runbook.kdl"))
    resolved = resolve_run_context(
        runbook=runbook,
        config_layers=[ConfigLayer.from_source(ConfigSource(location="tests/e2e/environment.conf", name="envConf"))],
        input_overrides={},
        project_dir="/repo",
    )
    commands = expand_runbook(runbook, resolved.to_context_frame())

    assert [c.identity for c in commands] == [
        "debug logging replay[shard11].Enable debug logging",
        "debug logging replay[shard11].Start Blackbird",
        "debug logging replay[shard11].Show debug log",
    ]
    assert all(c.context.kind == "ssh" for c in commands)
    assert commands[0].context.values["host"] == "flockr-fedora-shard-a"
    assert "loggingLevel=DEBUG" in commands[0].args[1]
    assert "log.level=DEBUG" in commands[0].args[1]
    assert commands[1].executable == "app/trading/bin/start.sh"
    assert commands[2].executable == "cat"
    assert commands[2].args == ["log/trading/blackbird.log"]


def test_e2e_replay_runbook_expands_over_deploy_instances() -> None:
    runbook = load_kdl_runbook(Path("tests/e2e/replay-runbook.kdl"))
    resolved = resolve_run_context(
        runbook=runbook,
        config_layers=[ConfigLayer.from_source(ConfigSource(location="tests/e2e/environment.conf", name="envConf"))],
        input_overrides={},
        project_dir="/repo",
    )
    commands = expand_runbook(runbook, resolved.to_context_frame())

    assert [c.identity for c in commands] == [
        "replay[shard-a].run-replay",
        "replay[shard-a].show-replay-output",
        "replay[shard-b].run-replay",
        "replay[shard-b].show-replay-output",
    ]
    assert all(c.context.kind == "ssh" for c in commands)
    assert commands[0].context.values["host"] == "flockr-fedora-shard-a"
    assert commands[2].context.values["host"] == "flockr-fedora-shard-b"
    assert commands[0].executable == "java"
    assert "--trade-ids" in commands[0].args
    assert commands[1].executable == "cat"
    assert commands[1].args == ["data/replay/replay.out"]
