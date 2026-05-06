# Codex Tips

## Keeping A Session Open

Leaving a Codex session open is usually helpful while the work is still connected.
The assistant keeps more project context: design decisions, branch/worktree setup,
what was already tried, and what not to repeat.

The tradeoff is context clutter. In a long session, old ideas can linger and make
the current goal less sharp.

Good habits:

- Keep the session open for active, related work.
- Start a new chunk by stating the current goal in one sentence.
- If the thread feels muddy, ask for: "summarize current state and reset focus."
- For major transitions, ask Codex to write a short handoff note into the repo.

For parallel experiments, prefer git worktrees over stash juggling. A worktree
keeps each branch in its own runnable directory with its own files, venv, and test
artifacts.

## Lesson: Slow Down At The Model Boundary

The KDL work improved when we stopped generating syntax and asked: what is the
right model?

Early drafts serialized Python-ish objects into KDL. The better shape came from
reading the KDL spec and examples, then mapping Flockr's real concepts onto the
language:

- `task` is the phase/expansion unit.
- `step` is one named action inside a task.
- `run` is structured argv.
- `shell` is trusted inline scripting.
- Properties are short modifiers.
- Child blocks are for structured details.

This is also the broader AI lesson. Strong models help, but they do not replace
clear architecture, sharp boundaries, or engineering taste. If the underlying
model is muddy, an agent can produce more code faster while making the muddiness
harder to unwind.

Use AI to accelerate implementation after the model is coherent. Use conversation,
examples, and tests to discover the model before committing to a shape.
