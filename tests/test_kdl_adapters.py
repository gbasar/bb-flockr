from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

import pytest

from flockr.config import ConfigSource
from flockr.config.kdl import load_kdl_config
from flockr.runbook.kdl import load_kdl_runbook


@dataclass
class FakeNode:
    name: str
    args: list[object] = field(default_factory=list)
    properties: dict[str, object] = field(default_factory=dict)
    children: list[FakeNode] = field(default_factory=list)


@dataclass
class FakeDocument:
    nodes: list[FakeNode]


def test_kdl_runbook_parses_tasks_config_sources_and_inputs(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    runbook_file = tmp_path / "runbook.kdl"
    runbook_file.write_text("ignored")
    document = FakeDocument(
        [
            FakeNode(
                "runbook",
                args=["local-demo"],
                children=[
                    FakeNode("config", args=["envConf"], properties={"source": "environment.conf"}),
                    FakeNode("config", args=["defaults.kdl"]),
                    FakeNode("input", args=["replay_id_file"], properties={"default": "ids.log"}),
                    FakeNode(
                        "task",
                        args=["inspect"],
                        properties={
                            "for_each": "${config.deploy.instances}",
                            "label": "${item.name}",
                        },
                        children=[
                            FakeNode(
                                "context",
                                args=["local"],
                                properties={"cwd": "${item.base_dir}"},
                            ),
                            FakeNode(
                                "command",
                                args=["print-instance"],
                                children=[
                                    FakeNode(
                                        "exec",
                                        args=[
                                            "printf",
                                            "instance=%s\n",
                                            "${item.name}",
                                        ],
                                    )
                                ],
                            ),
                        ],
                    ),
                ],
            )
        ]
    )
    install_fake_ckdl(monkeypatch, document)

    runbook = load_kdl_runbook(runbook_file)

    assert runbook.name == "local-demo"
    assert runbook.config_sources == [
        ConfigSource(location="environment.conf", name="envConf"),
        ConfigSource(location="defaults.kdl"),
    ]
    assert runbook.inputs == {"replay_id_file": "ids.log"}
    assert runbook.tasks[0].for_each == "${config.deploy.instances}"
    assert runbook.tasks[0].context is not None
    assert runbook.tasks[0].context.values == {"cwd": "${item.base_dir}"}
    assert runbook.tasks[0].commands[0].executable == "printf"


def test_load_kdl_runbook_reads_config_declarations_with_real_parser() -> None:
    runbook_file = Path("tests/fixtures/runbook-with-config.kdl")

    runbook = load_kdl_runbook(runbook_file)

    assert runbook.config_sources == [
        ConfigSource(location="environment.conf", name="envConf"),
        ConfigSource(location="defaults.kdl"),
    ]


def test_load_kdl_runbook_reads_task_step_run_shell_and_context_nodes(tmp_path: Path) -> None:
    runbook_file = tmp_path / "service-check.kdl"
    runbook_file.write_text('''
        runbook "service-check" {
            config "env" source="services.kdl"
            input "build" default="local"

            task Precheck {
                cwd "${project.dir}"

                step Workspace {
                    run pwd
                }

                step "Tool versions" {
                    shell """
                        python3 --version
                        git --version
                        """
                }
            }

            task "Check services" for_each="${config.env.services}" label="${item.name}" {
                ssh {
                    host "${item.host}"
                    user "${item.user}"
                }

                cwd "${item.dir}"

                step Summary {
                    run printf "service=%s build=%s\\n" "${item.name}" "${input.build}"
                }
            }
        }
        ''')

    runbook = load_kdl_runbook(runbook_file)

    assert runbook.name == "service-check"
    assert runbook.config_sources == [ConfigSource(location="services.kdl", name="env")]
    assert [task.name for task in runbook.tasks] == ["Precheck", "Check services"]
    assert runbook.tasks[0].context is not None
    assert runbook.tasks[0].context.kind == "local"
    assert runbook.tasks[0].context.values == {"cwd": "${project.dir}"}
    assert runbook.tasks[0].commands[0].name == "Workspace"
    assert runbook.tasks[0].commands[0].executable == "pwd"
    assert runbook.tasks[0].commands[1].name == "Tool versions"
    assert runbook.tasks[0].commands[1].executable == "sh"
    assert runbook.tasks[0].commands[1].args[0] == "-c"
    assert "python3 --version" in runbook.tasks[0].commands[1].args[1]
    assert runbook.tasks[1].for_each == "${config.env.services}"
    assert runbook.tasks[1].context is not None
    assert runbook.tasks[1].context.kind == "ssh"
    assert runbook.tasks[1].context.values == {
        "host": "${item.host}",
        "user": "${item.user}",
        "cwd": "${item.dir}",
    }
    assert runbook.tasks[1].commands[0].name == "Summary"
    assert runbook.tasks[1].commands[0].executable == "printf"


def test_load_kdl_runbook_reads_bare_if_fail_run(tmp_path: Path) -> None:
    runbook_file = tmp_path / "grep.kdl"
    runbook_file.write_text("""
        runbook "grep-demo" {
            task Search if_fail_run=#true {
                step "Find optional text" {
                    run grep needle file.txt
                }
            }
        }
        """)

    runbook = load_kdl_runbook(runbook_file)

    assert runbook.tasks[0].if_fail_run is True


def test_kdl_config_parses_item_children_as_list(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    config_file = tmp_path / "config.kdl"
    config_file.write_text("ignored")
    document = FakeDocument(
        [
            FakeNode(
                "deploy",
                children=[
                    FakeNode(
                        "instances",
                        children=[
                            FakeNode("item", properties={"name": "alpha", "base_dir": "/apps/a"}),
                            FakeNode("item", properties={"name": "beta", "base_dir": "/apps/b"}),
                        ],
                    )
                ],
            )
        ]
    )
    install_fake_ckdl(monkeypatch, document)

    config = load_kdl_config(config_file)

    assert config == {
        "deploy": {
            "instances": [
                {"name": "alpha", "base_dir": "/apps/a"},
                {"name": "beta", "base_dir": "/apps/b"},
            ]
        }
    }


def install_fake_ckdl(monkeypatch: pytest.MonkeyPatch, document: FakeDocument) -> None:
    fake_ckdl = ModuleType("ckdl")
    fake_ckdl.parse = lambda _text, version: document  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "ckdl", fake_ckdl)
