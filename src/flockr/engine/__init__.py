"""
ENGINE NOTE:
- Current SSH execution is subprocess-based and batch-oriented.
- Sticky SSH uses one remote shell script plus markers to split results.
- If we move to tmux or a persistent remote shell, we need an explicit per-command
  completion protocol, failure handling, and output boundary markers.
- Do not assume shell chaining or backgrounding will replace that protocol.
"""

from flockr.engine.executor import (
    CommandResult,
    Executor,
    LocalSubprocessExecutor,
    RecordingExecutor,
    RoutingExecutor,
    SshSubprocessExecutor,
    StickySshSubprocessExecutor,
    build_remote_command,
)
from flockr.engine.runner import RunEngine, RunResult
from flockr.engine.scheduler import Scheduler, SerialScheduler

__all__ = [
    "CommandResult",
    "Executor",
    "LocalSubprocessExecutor",
    "RecordingExecutor",
    "RoutingExecutor",
    "StickySshSubprocessExecutor",
    "SshSubprocessExecutor",
    "build_remote_command",
    "RunEngine",
    "RunResult",
    "Scheduler",
    "SerialScheduler",
]
