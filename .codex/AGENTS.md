# AGENTS.md — Codex Project Instructions

Codex should treat this file as the repo-local operating manual for Flockr.
Claude-specific instructions live in `CLAUDE.md` and `CLAUDE.local.md`; keep this
file aligned with them where the rules apply to Codex too.

## Critical Interaction Rule

- Before editing files, show the proposed diff or exact replacement text and wait
  for Greg's approval.
- Do not commit unless Greg explicitly asks for a commit.
- Do not push unless Greg explicitly asks for a push.
- If a task is read-only, do not modify files.

## Git Hygiene

- At session start in this repo, run `git status --short` and
  `git branch --show-current`.
- Do not work directly on `main`.
- Create or switch to a task branch before meaningful edits.
- Preserve uncommitted user changes. Never revert them unless Greg explicitly asks.

## Project Context

Flockr is a generic, config-driven command runner.

Core design constraints:
- Configuration layers are optional-present vs always-evaluated:
  `appConfig`, `userConfig`, and `projectConfig` may be absent; env vars,
  runbook, injection, and CLI are always evaluated.
- Flockr is format-agnostic internally. KDL is the primary authoring format, but
  YAML and HOCON are supported through serializers into an internal config model.
- Domain concepts such as Blackbird, shards, Solace replay, GitLab
  `environment.conf`, app servers, tenants, or regions must not be hardcoded into
  the engine.
- The reusable engine primitive is collection expansion: resolve config, select a
  collection from context, expand a task over it, execute each item in its context,
  and collate output per task instance.

## Engineering Standards

- Prefer small, explicit Python modules with type hints on all functions.
- Use modern Python syntax: `str | None`, `list[str]`, and Pydantic models at
  request/response or config boundaries.
- Use pytest, not unittest.
- Use `.venv/`; do not install packages globally.
- Run the repo's configured quality gates before claiming implementation work is
  complete.
- Keep docs in sync when behavior or commands change.

## Communication

- Be concise and direct.
- Surface assumptions early.
- When a requested path or instruction is wrong, say what was checked and what was
  actually found.
- For non-trivial work, present a short named-step plan before implementation.
