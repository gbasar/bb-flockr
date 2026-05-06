# Agents

## What Agents Are

Agents are separate Claude instances that spin up mid-task with their own system prompt,
restricted toolset, and focused purpose. The main Claude session decides when to invoke
them based on the `description` field in each agent file.

Key properties:
- They start cold — no memory of the conversation, just their system prompt + the task handed to them
- Their tools are explicitly restricted (e.g., read-only agents can't accidentally edit files)
- They run in parallel or in sequence as subagents, keeping specialized work out of main context
- The `description` field is what Claude reads to decide when to invoke them automatically

---

## Can You Make the Main Claude Wear a Hat?

Yes — two ways:

**Option A — Per-session (conversational):**
Just say "wear the python-grad hat for this session." The main Claude adopts the persona
without spawning a subagent. No config change needed. Works great for a focused work session.

**Option B — Permanent (settings.json):**
```json
{ "agent": "python-grad" }
```
This makes the main thread run as that agent on every session. Caveat: it also applies
the tool restrictions from the agent file, so you'd want to remove the `tools:` line from
`recent-ai-python-grad.md` first (tool restrictions make sense for subagents doing focused
read-only work, not for the main thread that needs to write code).

For day-to-day flockr work, Option A is probably right — invoke the hat when you need it,
drop it when you don't.

---

## Agents in This Project

### `python-grad` — `recent-ai-python-grad.md`
**The most useful one for daily work.**

Persona: PhD in AI, heavy Python background, pairing with a senior Java developer
to build something impressive. Opinionated about idiomatic Python, Martin Fowler
architecture principles, TDD, and Pydantic at every data boundary.

Why it's useful: Greg knows Java deeply. This agent will push back on Java-ish patterns
(e.g., over-engineered class hierarchies, manual null checks, verbose getters/setters)
and steer toward the Python way. It won't be polite about it — that's the point.

Invoke when: writing new modules, unsure if an approach is pythonic, need a second
opinion on architecture before committing to it.

---

### `code-reviewer` — `code-reviewer.md`
**Gate before any merge.**

Focused on correctness and maintainability: bugs, edge cases, type hint coverage,
Pydantic boundary enforcement, function/file size limits, ruff-detectable issues.

Why it's useful: read-only by design (Read, Grep, Glob only) — it can't make changes,
only report findings. Forces a clean review pass without the reviewer accidentally
"fixing" things while reviewing. Report format is specific: flag, location, fix.

Invoke when: pre-merge review, checking a PR, validating a module before calling it done.

---

### `security-auditor` — `security-auditor.md`
**Gate before any deployment.**

Checks for injection vulnerabilities, hardcoded secrets, subprocess shell injection,
insecure deserialization (pickle, yaml.load), auth gaps, and sensitive data leaking
into error responses or logs.

Why it's useful: security checks are easy to skip under deadline pressure. Making this
a named agent with a specific invocation point (pre-deploy) builds it into the workflow
rather than leaving it as a good intention. Read-only — reports findings, doesn't touch code.

Invoke when: before any docker push, before any release, when adding a new execution path.

---

### `flockr-config-validator` — `flockr-config-validator.md`
**Flockr-specific config and runbook reviewer.**

Understands the config layer precedence (appConfig → userConfig → projectConfig → env → CLI),
enforces dry-run/prod mode rules, checks that secrets stay in env vars, validates output
sink declarations, and flags configs that hardcode things that should use variable substitution.

Why it's useful: flockr's whole value proposition is correct config layering. This agent
knows the rules of that system and can catch violations before a runbook does something
unintended in production. Gets more useful as the project grows and runbooks multiply.

Invoke when: reviewing a new runbook, validating a config file, before running anything in prod mode.

---

## General Thoughts on Agents

**When they add real value:**
- The task is well-defined and self-contained (review this, audit that)
- You want a read-only pass that physically can't make changes
- You want a different "personality" or focus than the main thread
- The task is repetitive enough that a consistent system prompt produces consistent results

**When they don't help:**
- The task requires back-and-forth with the full conversation context
- You need the agent to make edits (better handled by the main thread)
- The scope is too fuzzy — agents work best with clear, bounded inputs

**The cold-start problem:**
Every agent starts with zero conversation context. If you invoke the code-reviewer
mid-session, it doesn't know what you've been building or why. You may need to hand
it a brief ("review src/config/loader.py — this is the KDL config parsing layer")
rather than just "review my code." More specific invocation = better output.
