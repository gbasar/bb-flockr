# Codex Workflow — Flockr

## Session Start

```bash
git status --short
git branch --show-current
```

If on `main` and meaningful work is planned, branch first:

```bash
git checkout -b feat/<task-name>
```

## Work Cycle

1. State the current goal in one sentence before starting
2. For non-trivial changes, present a named-step plan and wait for approval
3. Run quality gates after each meaningful change:
   ```bash
   .venv/bin/python -m pytest -q
   .venv/bin/python -m ruff check src tests
   ```
4. Commit only when asked

## Branch and Worktree Conventions

- `feat/<name>` — new feature
- `fix/<name>` — bug fix
- `refactor/<name>` — structural change without behavior change
- `docs/<name>` — documentation only

For parallel experiments, prefer git worktrees:

```bash
git worktree add .worktrees/<name> -b <branch>
```

Worktrees keep each branch in its own directory with its own venv and test
artifacts. Use them instead of stashing when you need to context-switch.

## Quality Gates (must pass before any merge)

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check src tests
docker build -t flockr:test . && docker run --rm flockr:test flockr --help
```

## Key Design Constraints

- Configuration layers are the central abstraction — do not encode layer precedence
  into function signatures; pass ordered layer lists
- Flockr is format-agnostic; KDL, HOCON, and YAML go through the same config
  interface — no format-specific logic outside `src/flockr/config/`
- Domain concepts (shard names, app paths, Solace VPNs) must not be hardcoded
  in the engine; they belong in config and runbooks
- `for_each` items run in parallel by default (limit: `config.default.parallel`);
  a failure stops the current item's steps but not other items
