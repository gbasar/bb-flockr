---
description: Full pre-merge review — correctness, style, test coverage, security gate
argument-hint: [branch or PR description]
---

Run a structured pre-merge review against the current branch diff.

## Review Checklist

**Correctness**
- Does the implementation match the stated intent?
- Are there edge cases the tests don't cover?
- Are error paths handled or explicitly documented as out of scope?

**Python Quality**
- Type hints on every function — parameters and return type
- No `Optional[X]` — use `X | None`
- Pydantic models at all data boundaries; no raw dicts crossing module lines
- Functions under 50 lines, files under 300 lines

**Tests**
- New behavior has tests; changed behavior has updated tests
- Test names describe behavior, not implementation
- No mocked DB or filesystem unless unavoidable

**Security**
- No secrets, tokens, or credentials in code or comments
- No `subprocess(shell=True)` with user-controlled input
- No `eval`, `exec`, or dynamic imports

**Docs**
- README, CLAUDE.md, and relevant project-docs updated if behavior changed
- New commands or hooks added to all required locations

## Output Format

For each finding:
```
[SEVERITY] file:line — description — recommended fix
```

Severities: `BLOCK` (must fix before merge), `WARN` (should fix), `NOTE` (consider later).

End with a one-line merge verdict: `APPROVE`, `APPROVE WITH NOTES`, or `BLOCK`.
