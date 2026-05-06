# Flockr — Architecture Decisions

Decisions made during early design review. Captured here so they don't get re-litigated.

---

## Format Agnosticism

**Decision:** Nothing in flockr is tied to KDL or any other config format.

The config module exposes a serializer/deserializer abstraction via `_CONFIG_LOADERS` in `config/load.py`. Any format can implement it by adding a `ConfigLoader` entry keyed on file extension. The engine works exclusively with flockr's internal config representation and never sees raw KDL or HOCON.

Implemented formats:
- **KDL** — default and recommended
- **HOCON** — optional install (`pip install flockr[hocon]`); HOCON substitutions are resolved, includes are not supported

Not yet implemented (trivially addable — two lines in `_CONFIG_LOADERS`):
- **YAML** — `.yaml` / `.yml`

**Enforcement:** Any format-specific library import outside the config serialization layer is a bug.

---

## Why KDL

**Decision:** KDL is the primary config format for flockr.

KDL was created by Kat Marchán, author of `npm ci` and Yarn — not a hobby project. The v2 spec is stable and production-ready.

For a command runner, KDL earns its place: nodes look like function calls, arguments and properties are first-class, blocks nest naturally. A runbook written in KDL reads like a script rather than serialized data. YAML or TOML would fight the domain.

Yes, it's niche. That's a tradeoff we're making deliberately — expressiveness over familiarity. If someone asks why not YAML: KDL was designed for exactly this kind of structured command/config use case. YAML was designed for data serialization and accreted config use later.

**Python library:** `ckdl` — C bindings, KDL v2 support, Python 3.13 wheels, actively maintained (v1.0 released December 2024). Evaluated against all three available Python KDL libraries.

---

## Config Layer Model

**Decision:** The layer diagram is not "mandatory vs overrideable" — it is **optional-present vs always-evaluated**.

The three file-based layers (appConfig, userConfig, projectConfig) are optional: each is skipped if absent. The mandatory layers (env vars, runbook, CLI) are always evaluated regardless.

| Layer | Source | Notes |
|---|---|---|
| `appConfig` | bundled package resource (`flockr-defaults.kdl`) | overrideable via CLI/env |
| `userConfig` | `~/.config/flockr/flockr.conf` | skipped if absent |
| `projectConfig` | `${project.dir}/conf/${project.name}.conf` | skipped if absent |
| runbook | specified at runtime | always evaluated |
| env vars | environment context | always evaluated |
| CLI | invocation arguments | always evaluated |

**Python "classpath" for bundled defaults:** `importlib.resources` — the file lives at `src/flockr/flockr-defaults.kdl` and is included in the wheel.

---

## Project Identity (project.dir / project.name)

`project.dir` is the working directory where `flockr` is invoked (`Path.cwd()`). `project.name` is derived from its basename.

`projectConfig` auto-discovery is not yet wired up. The file extension question (`.conf` vs `.kdl`) is deferred — see Open Questions.

---

## Config Discovery

**Decision:** Folders are discovered. Files are resolved.

When Flockr is pointed at a config container, such as a local directory or a remote
repository path, it should walk that container recursively. Directory names are
organization and identity. They are not config values and they are not merge layers.
Only config files become resolved config values.

Example:

```text
equityConfigs/
  dev/config.kdl
  test/qa/config.kdl
  test/sit/config.kdl
  test/uatf/config.kdl
  prod/pilot/config.kdl
  prod/prod/config.kdl
```

Flockr should discover these config leaves:

```text
dev
test/qa
test/sit
test/uatf
prod/pilot
prod/prod
```

The path to the file is the config identity. If there are more levels, the same rule
continues:

```text
test/qa/qa1/config.kdl -> test/qa/qa1
test/qa/qa2/config.kdl -> test/qa/qa2
```

This is path accumulation, not inheritance. `test` does not merge with `qa`, and
`qa1` does not overwrite `qa2`. Sibling config files are peers unless a future
runbook or CLI feature explicitly asks to combine them.

Resolution happens at the leaf file, after discovery has found it. Startup layers
such as app config, user preferences, project defaults, injected config, and CLI
overrides can be applied while resolving each leaf, but the directory path remains
identity/provenance, not merge semantics.

**Enforcement:** Do not treat directories as implicit config objects. Do not
deep-merge sibling config leaves. A recursive config-root feature must produce a
set of named leaves first, then resolve each leaf independently.

Initial implementation constraints:

- Use an explicit leaf filename such as `config.kdl` before treating a file as a
  discovered config leaf.
- Use the parent directory path relative to the discovery root as the leaf identity.
- Treat duplicate identities as startup errors, not precedence problems. For
  example, `qa.kdl` and `qa/config.kdl` must not silently compete for `qa`.
- Sort discovered leaves by identity before expansion so discovery order does not
  change logs, command identities, or task order.
- Do not add magic directory defaults such as `test/defaults.kdl` unless inheritance
  is introduced as an explicit feature with visible syntax.
- Normalize path segments before identity construction and reject ambiguous segments
  such as empty strings, `.`, `..`, or names containing path separators.

---

## Config Merge Semantics (DEFERRED)

List merge behavior (replace vs append across layers) is not yet defined. This will surface when implementing the config engine and must be resolved before writing multi-layer tests. Flag when we get there.

---

## Generic Runbook Expansion

**Decision:** Flockr's run engine is generic. It does not know domain concepts like
shards, queues, applications, regions, tenants, or environments.

Real operational use cases may start from domain-specific config, such as a HOCON
`environment.conf` containing hostnames, login users, base application directories,
or shard deployment data. Flockr treats that as just another optional config file
contributing structured data to the resolved context.

A runbook may select any collection from the resolved context and expand a task over
that collection. Each item is opaque to the engine. Domain meaning belongs to config
and runbook authors, not to flockr itself.

Example shape:

```kdl
task "replay" {
    for_each "${config.deploy.instances}"

    context "ssh" {
        host "${item.host}"
        user "${item.login}"
        cwd  "${item.base_dir}"
    }

    command "./bin/replay" args=[
        "--input", "${input.message_file}",
        "--target", "${item.name}"
    ]
}
```

The same primitive can drive Solace replay across 17 shards, a command across app
servers, work across Kubernetes namespaces, checks across database replicas, or any
other repeated operational task.

**Enforcement:** Avoid hardcoded first-class concepts like `shard`, `blackbird`,
`solace-replay`, or `environment.conf` in the engine. They may appear in examples,
plugins, or user config, but the core model is collection expansion plus execution
context plus command.

---

## Output Sink Architecture

Pluggable sinks. Four defined levels of complexity in the spec:

1. `stdout` — simple named sink
2. `file` with inline path
3. `file` with block config (rotation, size limits)
4. `solace` — enterprise plugin-grade with auth, QoS, retry, batching

Sinks are configured in the `output` block and routed by the Collator component of the run engine.

---

## Run Engine Components

Three clean concerns:

- **Context Creator** — prepares execution environment (local: cd to dir; remote: SSH, copy executables/payloads)
- **Executor** — runs individual tasks (v1: terminal commands with stdin/stdout)
- **Collator** — gathers output, routes to configured sinks

Natural Python pattern: async pipeline. SSH in v1 shells out to the local `ssh` binary via `asyncio.create_subprocess_exec` — this inherits `~/.ssh/config`, keys, proxy jumps, and agent forwarding for free. `asyncssh` was considered but rejected in favor of the simpler subprocess approach.

---

## TODO

- **Logging verbosity:** Log call sites are verbose (3-4 lines each). Refactor to a wrapper that collapses `logger.info("msg", extra=log_fields("PHASE", "event", ...))` into a single-line call.

---

## Open Questions

- Error handling / partial failure: if task 3 of 5 fails, stop or continue? Does the collator route errors separately?
- `appConfig` override mechanism: exact CLI flag / env var name TBD.
- **projectConfig file extension:** Should flockr look for `${project.name}.conf`, `${project.name}.kdl`, or probe both? If both exist, which wins? Current behavior (no auto-discovery wired up) is fine for v1 — deferred until there's a real use case at work to drive the decision.
- **env vars layer:** The config layer table lists env vars as "always evaluated" but the intent is unclear. Two possibilities: (a) flockr reads `os.environ` and exposes it as `config.env.FOO`, or (b) it simply means subprocesses inherit the ambient environment automatically. Option (b) is already true for free. Option (a) is not implemented. Needs a decision before the config layer model is considered complete.
