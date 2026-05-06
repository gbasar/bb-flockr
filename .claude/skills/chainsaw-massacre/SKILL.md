---
name: chainsaw-massacre
description: Use when asked to aggressively reduce code size, hunt useless code, remove duplication smells, collapse near-identical methods, or perform ChainSaw cleanup while preserving behavior.
---
# ChainSaw Massacre

Use this skill for code-weight-loss work: hunt useless bits of code, remove duplication smells, collapse repeated methods, and shrink the implementation while keeping behavior intact.

## Operating Rules

1. Measure before cutting: LOC, function/method count, and obvious duplication.
2. Work in one narrow unit: one file, one class, or one function family.
3. Do not edit more than three files in one pass unless the user explicitly asks.
4. Preserve behavior unless you identify and name a bug.
5. Prefer deleting, collapsing, or joining existing paths over adding new abstraction.
6. Extract an abstraction only when repeated structure is already visible and the smaller concept has a name.
7. Push back when a cut would make the code less clear, less correct, or harder to test.
8. Present findings before cutting. Do not silently jump from inspection to edits.
9. When Python files change, format with Black or run Black check if formatting was already clean.

## Workflow

1. Surface scan: find near-identical code, pass-through wrappers, repeated branches, unused names, helpers used once, and anything with a whiff of duplication.
2. Trace through: follow the shortest path from input to output and identify indirection that does not earn its keep.
3. Do more with less: ask whether two paths can become one path with data, a smaller helper, or direct code.
4. Present findings: duplication smells, useless-code suspects, shortest-path observations, and ranked cuts.
5. Name the first cut before making it.
6. Cut one unit: make the smallest coherent behavior-preserving change.
7. Format Python with Black when Python files changed.
8. Verify: run the narrowest relevant test, lint, or type check.
9. Report: show what shrank, what stayed unchanged, formatting, verification, and the next recommended cut.

## Report Format

```markdown
## Measurement
- Before:
- After:
- Reduction:

## Findings
- Duplication smells:
- Useless-code suspects:
- First cut:

## Cut
- Removed/simplified:
- Behavior preserved:
- Risk:

## Formatting
- Black:

## Verification
- Command:
- Result:

## Next
- Recommended next cut:
```
