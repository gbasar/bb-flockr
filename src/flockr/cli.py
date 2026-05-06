from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from flockr.config import ConfigLayer, ConfigSource, resolve_run_context
from flockr.config.resolve import parse_config_overrides
from flockr.engine import (
    LocalSubprocessExecutor,
    RoutingExecutor,
    RunEngine,
    SerialScheduler,
    StickySshSubprocessExecutor,
)
from flockr.logging import configure_logging, get_logger
from flockr.runbook import load_kdl_runbook

log = get_logger("flockr.cli")


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    if args.command == "run":
        try:
            return asyncio.run(_run(args))
        except (RuntimeError, TypeError, ValueError) as exc:
            print(f"flockr: {exc}", file=sys.stderr)
            return 1

    parser.print_help()
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flockr")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase debug logging. Use -v, -vv, or -vvv.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run = subparsers.add_parser("run", help="Run a KDL runbook")
    run.add_argument("runbook", help="Path to runbook KDL file")
    run.add_argument(
        "--config",
        action="append",
        default=[],
        help=(
            "Path to a config file, or NAME=PATH to load it under config.NAME. "
            "Supported local formats: .kdl, .conf, .hocon."
        ),
    )
    run.add_argument(
        "--input",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Input override for the runbook",
    )
    run.add_argument(
        "--override-file",
        action="append",
        default=[],
        help="Path to a config override file, or NAME=PATH to load it under config.NAME.",
    )
    run.add_argument(
        "--override",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Config override using a dotted key path, for example envConf.logging.level=debug.",
    )

    return parser


async def _run(args: argparse.Namespace) -> int:
    log.info("RUNBOOK", "runbook.load", path=args.runbook)
    runbook = load_kdl_runbook(args.runbook)
    project_dir = str(Path.cwd())
    log.debug("CLI", "project.dir", project_dir=project_dir)
    log.info("CONFIG", "config.load", config_count=len(args.config))
    for path in args.config:
        log.debug("CONFIG", "config.layer.load", path=path)
    resolved_context = resolve_run_context(
        runbook=runbook,
        config_layers=_config_layers(args, runbook.config_sources),
        input_overrides=dict(_assignments(args.input, "Input overrides must use KEY=VALUE")),
        project_dir=project_dir,
    )
    log.debug("RUNBOOK", "input.resolve", input_names=sorted(resolved_context.inputs))

    context = resolved_context.to_context_frame()
    parallel = resolved_context.config.get("default", {}).get("parallel", 2)
    executor = RoutingExecutor(
        {
            "local": LocalSubprocessExecutor(),
            "ssh": StickySshSubprocessExecutor(),
        }
    )
    engine = RunEngine(SerialScheduler(executor, parallel=parallel))
    result = await engine.run(runbook, context)

    exit_code = 0
    for command_result in result.results:
        command = command_result.command
        print(f"{command.identity}: exit={command_result.exit_code}")
        if command_result.stdout:
            print(command_result.stdout, end="")
        if command_result.stderr:
            print(command_result.stderr, end="", file=sys.stderr)
        exit_code = max(exit_code, command_result.exit_code)

    return exit_code


def _config_layers(args: argparse.Namespace, runbook_sources: list[ConfigSource]) -> list[ConfigLayer]:
    layers = [
        *[ConfigLayer.from_source(source) for source in runbook_sources],
        *[ConfigLayer.from_source(_parse_config_source(source)) for source in args.config],
        *[ConfigLayer.from_source(_parse_config_source(source)) for source in args.override_file],
    ]
    overrides = parse_config_overrides(_assignments(args.override, "Config overrides must use KEY=VALUE"))
    if overrides:
        layers.append(ConfigLayer.from_values(overrides))
    return layers


def _assignments(raw_values: list[str], usage: str) -> list[tuple[str, str]]:
    return [_require_assignment(raw_value, usage) for raw_value in raw_values]


def _parse_config_source(raw_source: str) -> ConfigSource:
    parsed = _parse_assignment(raw_source)
    if parsed is None:
        return ConfigSource(location=raw_source)

    name, location = parsed
    if not name or not location:
        raise ValueError(f"Config source must be PATH or NAME=PATH: {raw_source}")

    return ConfigSource(location=location, name=name)


def _parse_assignment(raw_value: str) -> tuple[str, str] | None:
    key, separator, value = raw_value.partition("=")
    if separator == "":
        return None
    return key, value


def _require_assignment(raw_value: str, usage: str) -> tuple[str, str]:
    parsed = _parse_assignment(raw_value)
    if parsed is None or not parsed[0]:
        raise ValueError(f"{usage}: {raw_value}")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
