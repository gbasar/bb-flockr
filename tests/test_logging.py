import logging

from conftest import ssh_command

from flockr.logging import FlockrLogFormatter, command_fields, log_fields


def test_flockr_formatter_renders_phase_event_and_fields() -> None:
    record = logging.LogRecord(
        name="flockr.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="loaded runbook",
        args=(),
        exc_info=None,
    )
    for key, value in log_fields(
        "RUNBOOK",
        "runbook.load",
        path="examples/local-runbook.kdl",
        command_count=2,
    ).items():
        setattr(record, key, value)

    formatted = FlockrLogFormatter().format(record)

    assert formatted == ("INFO RUNBOOK runbook.load loaded runbook " "command_count=2 path=examples/local-runbook.kdl")


def test_flockr_formatter_handles_plain_log_records() -> None:
    record = logging.LogRecord(
        name="flockr.test",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="plain warning",
        args=(),
        exc_info=None,
    )

    assert FlockrLogFormatter().format(record) == "WARNING plain warning"


def test_command_fields_match_resolved_execution_plan_names() -> None:
    command = ssh_command("run", task_name="replay", task_item="shard1", runbook_name="ops", executable="java")

    assert command_fields(command) == {
        "identity": "replay[shard1].run",
        "runbook": "ops",
        "task": "replay",
        "item": "shard1",
        "command": "run",
        "context": "ssh",
    }
