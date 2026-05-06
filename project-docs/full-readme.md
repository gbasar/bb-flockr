# Flockr Full Guide

This is the longer project guide. The top-level [README](../README.md) is the
short version.

## What Flockr Is

Flockr is a generic, config-driven command runner for operational work.

It is for situations where the important facts already live in configuration:
hosts, users, install directories, regions, shards, queues, tenants, app instances,
or whatever else a team uses to describe the systems it operates.

Flockr does not know what those things mean. It loads config, gives runbooks a
structured context, expands tasks over the collections the runbook points at, runs
commands in the declared execution context, and records what happened.

## Config Shape

Real environment config may look roughly like this:

```hocon
install {
  directory = "/local/1/app/test"
  user = testuser
}

replay {
  jar_url = "https://nexus.example/repository/tools/replay.jar"
}

trading {
  shard {
    1 {
      primary.host = testhost1
      primary.directory = ${install.directory}"/shard_1"
    }

    2 {
      primary.host = testhost2
      primary.directory = ${install.directory}"/shard_2"
    }
  }
}
```

That file is application config, not Flockr config. To avoid collisions with
Flockr-owned names, load it under a namespace:

```kdl
runbook "replay" {
    config "envConf" source="environment.conf"
}
```

The runbook reads it under `config.envConf`.

## Replay Artifact Example

A runbook can do local setup first, then expand remote work over config. This is
the rough shape for downloading a replayer from Nexus, pushing it to each shard,
and running it:

```kdl
runbook "replay" {
    config "envConf" source="environment.conf"
    input "replay_id_file"

    task "download-replayer" {
        context "local" cwd="${project.dir}"

        command "download" {
            exec "curl" "-L" "-o" "build/replay.jar" "${config.envConf.replay.jar_url}"
        }
    }

    task "push-and-run" for_each="${config.envConf.trading.shard}" {
        context "ssh" host="${item.primary.host}" user="${config.envConf.install.user}" cwd="${item.primary.directory}"

        command "push" {
            context "local"
            exec "scp" "build/replay.jar" "${config.envConf.install.user}@${item.primary.host}:${item.primary.directory}/replay.jar"
        }

        command "verify" {
            exec "test" "-s" "replay.jar"
        }

        command "run" {
            exec "java" "-jar" "replay.jar" "--ids" "${input.replay_id_file}"
        }
    }
}
```

SSH contexts are sticky by default. Flockr runs consecutive commands for the
same expanded task item in one SSH process when they share the same resolved SSH
context. In the example, `verify` and `run` share one SSH process. That reduces
repeated SSH login banners on systems that print long interactive notices. Commands
with their own context, such as the local `scp` above, still run in their declared
context. Use `sticky=false` on an SSH context to opt out.

## Config Discovery

The current prototype loads individual config files with runbook `config`
declarations or CLI `--config`. A planned bootstrap feature is recursive config
discovery from a directory or repository path.

The rule is simple:

```text
Folders are discovered. Files are resolved.
```

For example, a config root might look like this:

```text
equityConfigs/
  dev/config.kdl
  test/qa/config.kdl
  test/sit/config.kdl
  test/uatf/config.kdl
  prod/pilot/config.kdl
  prod/prod/config.kdl
```

Flockr would discover six config names:

```text
dev
test/qa
test/sit
test/uatf
prod/pilot
prod/prod
```

A folder groups configs. It is not a merged config. A file defines one config, and
the path to that file names it. Extra levels follow the same rule:
`test/qa/qa1/config.kdl` becomes `test/qa/qa1`.

Config is resolved before commands run. Commands can read config, but they do not
change it. Runtime downloads are command outputs or artifacts, not config overrides.

## Quick SSH Smoke Test

For a quick test against a host from your OpenSSH config:

```bash
.venv/bin/python -m flockr.cli -vv run examples/ssh-smoke.kdl --input host=my-ssh-alias
```

The smoke runbook executes `whoami`, `hostname`, and `pwd` over SSH. Flockr shells
out to the local `ssh` binary, so aliases, keys, proxy jumps, and users from
`~/.ssh/config` still apply. The SSH executor uses `BatchMode=yes`, so interactive
password prompts are not expected to work.

## Install For Development

Create a virtual environment and install the project:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

HOCON support is optional so the base package stays small. Install it when loading
`.conf` or `.hocon` files:

```bash
.venv/bin/python -m pip install -e ".[dev,hocon]"
```

`uv` is optional. The project supports plain `pip`.

## Run The Current Prototype

Local KDL demo:

```bash
.venv/bin/python -m flockr.cli -v run examples/local-runbook.kdl --config envConf=examples/local-config.kdl
```

Expected output shape:

```text
inspect[alpha].print-instance: exit=0
instance=alpha ids=/path/to/flockr/resources/ids_to_replay.log
inspect[beta].print-instance: exit=0
instance=beta ids=/path/to/flockr/resources/ids_to_replay.log
```

## Docker SSH Lab

For manual host-side testing against disposable SSH targets, start the lab:

```bash
scripts/dev.sh lab
```

`lab` publishes random host ports for the SSH containers and writes the discovered
ports to `build/lab/environment.kdl`. The lab stays running until you stop it.

Create a tiny local runbook:

```bash
mkdir -p build/lab
cat > build/lab/smoke.kdl <<'EOF'
runbook "lab-smoke" {
    task "inspect" for_each="${config.envConf.deploy.instances}" {
        context "ssh" host="${item.host}" port="${item.port}" user="${item.login}" identity_file="${item.identity_file}" cwd="${item.base_dir}"

        command "whoami" {
            exec "whoami"
        }

        command "where-am-i" {
            exec "pwd"
        }
    }
}
EOF
```

Run it from your host Python against the generated lab config:

```bash
.venv/bin/python -m flockr.cli -vv run build/lab/smoke.kdl --config envConf=build/lab/environment.kdl
```

Stop the lab when finished:

```bash
scripts/dev.sh lab-down
```

## Tests

Fast tests:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check src tests
```

Full verification:

```bash
scripts/dev.sh full
```

## Current Status

Implemented:

- KDL runbook loading
- KDL config loading
- optional HOCON config loading by extension
- named config sources such as `envConf=environment.conf`
- runbook-declared bootstrap config sources such as `config "envConf" source="environment.conf"`
- override files and dotted CLI config overrides
- task expansion with `for_each`
- map iteration using the map key as `item.name`
- command identity such as `replay[shard-a].run`
- local subprocess execution
- SSH execution through the local `ssh` binary
- sticky SSH command grouping by default for repeated commands in the same expanded task item
- developer-facing lifecycle logging with `phase` and `event` fields
- command logs with resolved-plan fields: `runbook`, `task`, `item`, `command`, `context`, and `identity`
- opt-in full verification through `scripts/dev.sh full`
- host-side Docker SSH lab through `scripts/dev.sh lab`

Current TODO list:

1. Finish default config bootstrap policy for app, user, project, env, and recursive config-root discovery.
2. Defer output collation, file sinks, JSON/NDJSON rendering, and parallel execution until the core config/runbook path is steadier.
3. Decide execution failure semantics: stop-on-failure first, continue/parallel later.
