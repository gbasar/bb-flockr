# CLAUDE.md — Project Instructions

## Critical Rules

### 0. NEVER Publish Sensitive Data
- NEVER commit passwords, API keys, tokens, or secrets to git/pip/docker
- NEVER commit `.env` files — ALWAYS verify `.env` is in `.gitignore`
- Before ANY commit: verify no secrets are included
- NEVER output secrets in suggestions, logs, or responses


### 1. Git Workflow — NEVER Work Directly on Main

**Auto-branch is ON by default.** A hook blocks commits to `main`. To avoid wasted work, **ALWAYS check and branch BEFORE editing any files:**

```bash
# MANDATORY first step — do this BEFORE writing or editing anything:
git branch --show-current
# If on main → create a feature branch IMMEDIATELY:
git checkout -b feat/<task-name>
# NOW start working.
```

**Branch naming conventions:**
- `feat/<name>` — new features
- `fix/<name>` — bug fixes
- `docs/<name>` — documentation changes
- `refactor/<name>` — code refactors
- `test/<name>` — test additions

**Why branch FIRST, not at commit time:**
- The `check-branch.sh` hook blocks `git commit` on `main`
- If you edit 10 files on `main` then try to commit, you'll be blocked and have to branch retroactively
- Branching first costs 1 second. Branching after being blocked wastes time and creates messy history.

- Use `/worktree <branch-name>` when you want a separate directory (parallel sessions)
- If Claude screws up on a feature branch, delete it — main is untouched

**Before merging any branch back to main:**
1. Review the full diff: `git diff main...HEAD`
2. Ask the user: "Do you want RuleCatch to check for violations on this branch?"
3. Only merge after the user confirms

**Why this matters:**
- Main should always be deployable
- Feature branches are disposable — delete and start over if needed
- `git diff main...HEAD` shows exactly what changed, making review easy
- Auto-branching means zero friction — you don't have to remember
- Worktrees let you run multiple Claude sessions in parallel without conflicts
- RuleCatch catches violations Claude missed — last line of defense before merge


## When Something Seems Wrong

Before jumping to conclusions:

- Missing behavior? → Check feature gates BEFORE assuming bug
- Empty data? → Check if services are running BEFORE assuming broken
- 404 error? → Check service separation BEFORE adding endpoint
- Auth failing? → Check which auth system BEFORE debugging
- Test failing? → Read the error message fully BEFORE changing code

---

## Python

When working on a Python project (detected by `pyproject.toml` in root):

- **Type hints ALWAYS:** Every function MUST have type hints for all parameters AND return type
- **Modern syntax:** Use `str | None` (not `Optional[str]`), `list[str]` (not `List[str]`)
- **Async consistently:** FastAPI handlers must be `async def` for I/O operations
- **pytest only:** NEVER use unittest — use pytest with `@pytest.mark.parametrize` for table-driven tests
- **Virtual environment:** ALWAYS use `.venv/` — NEVER install packages globally
- **Pydantic models:** Use Pydantic `BaseModel` for all request/response schemas
- **Pydantic settings:** Use `pydantic-settings` `BaseSettings` for environment config
- **ruff:** Run `ruff check` before committing — config in `pyproject.toml`
- **API versioning:** All endpoints under `/api/v1/` prefix
- **Quality gates:** No file > 300 lines, no function > 50 lines
- **Makefile:** Use `make dev`, `make test`, `make lint` — NOT raw Python commands in scripts
- **Graceful shutdown:** Handle SIGINT/SIGTERM, close connections before exiting


## Testing

### Unit and Integration
- Martin Fowler test pyramid: unit → integration → e2e
- Tests hit a real local DB — never mock the database layer
- Functional tests must fully bootstrap the app before running — not just mocks
  (e.g., if it's a web server, spin it up; if it uses Solace, spin up Solace via container)
- Test config lives in `src/test/resources/` — not in the source tree
- Tests describe behavior, not implementation

### Final Test — Docker
The last gate before any merge or release is a full Docker run:

1. Build the image: `docker build -t flockr:test .`
2. Run it: `docker run --rm -d --name flockr-test flockr:test`
3. Wait for startup (poll health or wait 5s)
4. Verify it's still running: `docker ps | grep flockr-test`
5. Exercise it — SSH in, hit the CLI, or call the health endpoint depending on what flockr exposes
6. Check logs for fatal errors: `docker logs flockr-test`
7. Clean up: `docker stop flockr-test`

If any step fails: STOP. Show what failed. Do NOT merge or push.


## Naming — NEVER Rename Mid-Project

Renaming packages, modules, or key variables mid-project causes cascading failures that are extremely hard to catch. If you must rename:

1. Create a checklist of ALL files and references first
2. Use IDE semantic rename (not search-and-replace)
3. Full project search for old name after renaming
4. Check: .md files, .txt files, .env files, comments, strings, paths
5. Start a FRESH Claude session after renaming

---

## Plan Mode — Plan First, Code Second
**For any non-trivial task, start in plan mode.** Don't let Claude write code until you've agreed on the plan. Bad plan = bad code. Always.

- Use plan mode for: new features, refactors, architectural changes, multi-file edits
- Skip plan mode for: typo fixes, single-line changes, obvious bugs
- One Claude writes the plan. You review it as the engineer. THEN code.

### Step Naming — MANDATORY

Every step in a plan MUST have a consistent, unique name. This is how the user references steps when requesting changes. Claude forgets to update plans — named steps make it unambiguous.

```
CORRECT — named steps the user can reference:
  Step 1 (Project Setup): Initialize repo with pyproject.toml
  Step 2 (Config Layer): Implement KDL config loading
  Step 3 (Run Engine): Build the runbook executor
  Step 4 (Output Sinks): Add stdout and file sinks
  Step 5 (Testing): Write integration tests with Docker

WRONG — generic steps nobody can reference:
  Step 1: Set things up
  Step 2: Build the backend
  Step 3: Add tests
```

### Modifying a Plan — REPLACE, Don't Append

When the user asks to change something in the plan:

1. **FIND** the exact named step being changed
2. **REPLACE** that step's content entirely with the new approach
3. **Review ALL other steps** for contradictions with the change
4. **Rewrite the full updated plan** so the user can see the complete picture

```
CORRECT:
  User: "Change Step 3 (Run Engine) to support parallel execution"
  Claude: Replaces Step 3 content, checks Steps 4-5 for conflicts,
          outputs the FULL updated plan with Step 3 rewritten

WRONG:
  User: "Actually make it parallel"
  Claude: Appends "Also, use parallel execution" at the bottom
          ← Step 3 still says single-threaded. Plan now contradicts itself.
```

**Claude will forget to do this.** If you notice the plan has contradictions, tell Claude: "Rewrite the full plan — Step 3 and Step 7 contradict each other."

- If fundamentally changing direction: `/clear` → state requirements fresh

---

## Documentation Sync

When updating any feature, keep these locations in sync:

1. `README.md` (repository root)
2. `project-docs/` (relevant documentation)
3. `CLAUDE.md` quick reference table (if adding commands/scripts)
4. Inline code comments
5. Test descriptions

If you update one, update ALL.

### Adding a New Command or Hook — MANDATORY Checklist

When creating a new `.claude/commands/*.md` or `.claude/hooks/*.sh`:

1. **README.md** — Update the command count, project structure tree, and add a description section
2. **CLAUDE.md** — Add to the quick reference table (if user-facing)
3. **.claude/settings.json** — Wire up hooks (if adding a hook)

**This is NOT optional.** Every command/hook must appear in all locations before the commit.

## CLAUDE.md Is Team Memory — The Feedback Loop

Every time Claude makes a mistake, **add a rule to prevent it from happening again.**

This is the single most powerful pattern for improving Claude's behavior over time:

1. Claude makes a mistake (wrong pattern, bad assumption, missed edge case)
2. You fix the mistake
3. You tell Claude: "Update CLAUDE.md so you don't make that mistake again"
4. Claude adds a rule to this file
5. Mistake rates actually drop over time

**This file is checked into git. The whole team benefits from every lesson learned.**

Don't just fix bugs — fix the rules that allowed the bug. Every mistake is a missing rule.

---

## Workflow Preferences
- Quality over speed — if unsure, ask before executing
- Plan first, code second — use plan mode for non-trivial tasks
- One task, one chat — `/clear` between unrelated tasks
- One task, one branch — use `/worktree` to isolate work from main
- Use `/context` to check token usage when working on large tasks
- When testing: queue observations, fix in batch (not one at a time)
- Research shows 2% misalignment early in a conversation can cause 40% failure rate by end — start fresh when changing direction