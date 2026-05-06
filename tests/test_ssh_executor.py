from pathlib import Path

from conftest import ssh_command

from flockr.engine import build_remote_command
from flockr.engine.executor import build_sticky_remote_command, split_sticky_results


def test_remote_command_includes_cwd_and_quoted_args() -> None:
    command = ssh_command(
        "run", cwd="/apps/demo dir", executable="java", args=["-jar", "toy app.jar", "--ids", "data/replay ids.txt"]
    )

    assert build_remote_command(command) == (
        "cd '/apps/demo dir' && java -jar 'toy app.jar' --ids 'data/replay ids.txt'"
    )


def test_remote_command_without_cwd_is_just_the_executable() -> None:
    command = ssh_command("uptime", executable="uptime")

    assert build_remote_command(command) == "uptime"


def test_sticky_results_keeps_stdout_stderr_and_exit_code_per_command() -> None:
    commands = [ssh_command("one"), ssh_command("two")]

    results = split_sticky_results(
        commands,
        Path("tests/fixtures/sticky-stdout.txt").read_text(),
        Path("tests/fixtures/sticky-stderr.txt").read_text(),
    )

    assert [r.exit_code for r in results] == [0, 2]
    assert [r.stdout for r in results] == ["login banner\none stdout\n", "two stdout\n"]
    assert [r.stderr for r in results] == ["one stderr\n", "two stderr\n"]


def test_sticky_results_omits_commands_that_never_ran() -> None:
    commands = [ssh_command("one"), ssh_command("two")]

    results = split_sticky_results(
        commands,
        "__FLOCKR_TOKEN_START_0__\none stdout\n__FLOCKR_TOKEN_EXIT_0__:2\n",
        "__FLOCKR_TOKEN_START_0__\none stderr\n__FLOCKR_TOKEN_EXIT_0__:2\n",
    )

    assert [r.command.command_name for r in results] == ["one"]
    assert [r.exit_code for r in results] == [2]


def test_sticky_remote_script_exits_on_first_command_failure() -> None:
    command = ssh_command("one")

    remote_command = build_sticky_remote_command([command])

    assert 'if [ "$_flockr_code" -ne 0 ]; then exit "$_flockr_status"; fi' in remote_command
