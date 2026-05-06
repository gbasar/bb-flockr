from __future__ import annotations

import logging
from typing import Any

_RESERVED_RECORD_KEYS = set(
    logging.LogRecord(
        name="",
        level=0,
        pathname="",
        lineno=0,
        msg="",
        args=(),
        exc_info=None,
    ).__dict__
) | {"asctime", "message"}


class FlockrLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        parts = [record.levelname]

        phase = getattr(record, "phase", None)
        if phase is not None:
            parts.append(str(phase))

        event = getattr(record, "event", None)
        if event is not None:
            parts.append(str(event))

        parts.append(record.getMessage())

        extras = [
            (key, value)
            for key, value in sorted(record.__dict__.items())
            if key not in _RESERVED_RECORD_KEYS and key not in {"phase", "event"}
        ]
        parts.extend(f"{key}={_format_value(value)}" for key, value in extras)

        return " ".join(parts)


def configure_logging(verbosity: int) -> None:
    if verbosity <= 0:
        level = logging.WARNING
    elif verbosity == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG

    handler = logging.StreamHandler()
    handler.setFormatter(FlockrLogFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.WARNING)

    logging.getLogger("flockr").setLevel(level)


def log_fields(phase: str, event: str, **fields: Any) -> dict[str, Any]:
    return {"phase": phase, "event": event, **fields}


class FlockrLogger:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def debug(self, phase: str, event: str, **fields: Any) -> None:
        self._logger.debug(event, extra=log_fields(phase, event, **fields))

    def info(self, phase: str, event: str, **fields: Any) -> None:
        self._logger.info(event, extra=log_fields(phase, event, **fields))

    def warning(self, phase: str, event: str, **fields: Any) -> None:
        self._logger.warning(event, extra=log_fields(phase, event, **fields))


def get_logger(name: str) -> FlockrLogger:
    return FlockrLogger(logging.getLogger(name))


def command_fields(command: Any) -> dict[str, Any]:
    fields = {
        "identity": command.identity,
        "runbook": command.runbook_name,
        "task": command.task_name,
        "command": command.command_name,
        "context": command.context.kind,
    }
    if command.task_item is not None:
        fields["item"] = command.task_item
    return fields


def _format_value(value: Any) -> str:
    if isinstance(value, str) and value and not any(character.isspace() for character in value):
        return value
    return repr(value)
