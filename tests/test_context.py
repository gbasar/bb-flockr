import pytest

from flockr.context import ContextFrame


def test_child_context_reads_parent_values() -> None:
    root = ContextFrame({"project": {"dir": "/repo"}})
    child = root.child({"item": {"name": "instance-01"}})

    assert child.get("project") == {"dir": "/repo"}
    assert child.get("item") == {"name": "instance-01"}


def test_child_context_overrides_parent_values() -> None:
    root = ContextFrame({"cwd": "/repo"})
    child = root.child({"cwd": "/repo/subdir"})

    assert child.get("cwd") == "/repo/subdir"


def test_context_resolves_dotted_paths() -> None:
    context = ContextFrame({"config": {"deploy": {"instances": [{"name": "instance-01"}]}}})

    assert context.get("config.deploy.instances.0.name") == "instance-01"


def test_missing_value_raises_key_error() -> None:
    context = ContextFrame()

    with pytest.raises(KeyError):
        context.get("missing")


def test_flatten_merges_outer_to_inner() -> None:
    root = ContextFrame({"cwd": "/repo", "project": "flockr"})
    child = root.child({"cwd": "/repo/subdir"})

    assert child.flatten() == {"cwd": "/repo/subdir", "project": "flockr"}
