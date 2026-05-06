from __future__ import annotations

from pydantic import BaseModel

from flockr.context import ContextFrame
from flockr.engine.executor import CommandResult
from flockr.engine.scheduler import Scheduler
from flockr.logging import get_logger
from flockr.runbook import Runbook, expand_runbook

log = get_logger(__name__)


class RunResult(BaseModel):
    results: list[CommandResult]


class RunEngine:
    def __init__(self, scheduler: Scheduler) -> None:
        self.scheduler = scheduler

    async def run(self, runbook: Runbook, context: ContextFrame) -> RunResult:
        log.info("ENGINE", "runbook.start", runbook_name=runbook.name)
        commands = expand_runbook(runbook, context)
        log.info("RUNBOOK", "runbook.expand", runbook_name=runbook.name, command_count=len(commands))  # noqa: E501
        results = await self.scheduler.run_all(commands)
        log.info("ENGINE", "runbook.finish", runbook_name=runbook.name, result_count=len(results))
        return RunResult(results=results)
