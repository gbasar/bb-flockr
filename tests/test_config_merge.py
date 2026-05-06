from flockr.config import deep_merge


def test_deep_merge_preserves_unmentioned_nested_values() -> None:
    merged = deep_merge(
        {"envConf": {"logging": {"level": "info"}, "runtime": {"threads": 1}}},
        {"envConf": {"logging": {"level": "debug"}}},
    )

    assert merged == {
        "envConf": {
            "logging": {"level": "debug"},
            "runtime": {"threads": 1},
        }
    }


def test_deep_merge_replaces_lists() -> None:
    merged = deep_merge({"targets": ["one"]}, {"targets": ["two"]})

    assert merged == {"targets": ["two"]}


def test_deep_merge_does_not_mutate_inputs() -> None:
    base = {"runtime": {"threads": 1}}
    override = {"runtime": {"threads": 4}}

    deep_merge(base, override)

    assert base == {"runtime": {"threads": 1}}
    assert override == {"runtime": {"threads": 4}}
