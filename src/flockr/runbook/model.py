from __future__ import annotations

from pydantic import BaseModel, Field

from flockr.config import ConfigSource


class ExecutionContext(BaseModel):
    kind: str
    values: dict[str, str] = Field(default_factory=dict)


class Command(BaseModel):
    name: str
    context: ExecutionContext | None = None
    executable: str
    args: list[str] = Field(default_factory=list)


class Task(BaseModel):
    name: str
    for_each: str | None = None
    label: str | None = None
    if_fail_run: bool = False
    context: ExecutionContext | None = None
    commands: list[Command]


class Runbook(BaseModel):
    name: str
    config_sources: list[ConfigSource] = Field(default_factory=list)
    inputs: dict[str, str] = Field(default_factory=dict)
    context: ExecutionContext | None = None
    tasks: list[Task]


class CommandInstance(BaseModel):
    identity: str
    runbook_name: str
    task_name: str
    task_item: str | None = None
    command_name: str
    context: ExecutionContext
    executable: str
    args: list[str] = Field(default_factory=list)
    if_fail_run: bool = False
