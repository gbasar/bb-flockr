# Flockr

![Flockr](project-docs/icons/flockr-flock.svg)

Flockr is a config-driven task executor for operational runbooks.

## Flockr By Example

This README highlights three replay-shaped support tasks:

1. Replay all outbound transaction logs over Solace, limited by message type and order IDs.
2. Replay one shard to generate verbose logging.
3. Stage one shard with the JVM waiting for a debugger.

The examples are Blackbird-heavy, but the model is generic: load config, resolve inputs, expand tasks, and run named steps in local or SSH context.

## 1. Replay Outbound Subset Of Trade Events Over Solace (All Shards)

```kdl
runbook "blackbird-replay" {
    // 1. Load config. This can be a local file or an HTTP(S) URL.
    // Flockr reads .conf/.hocon as HOCON.
    config "env" source="https://gitlab.example.com/blackbird/prod/environment.conf"

    // 2. Resolve inputs. This is the local path to one order/ExecID per line.
    input "order_ids_file" default="orders-to-replay.txt"

    // Step names are not decoration. They become result/log labels.
    task "Prepare local replay inputs" {
        local {
            cwd "${project.dir}"
        }

        step "Check order id file" {
            run test -s "${input.order_ids_file}"
        }

        step "Show target environment" {
            run printf "solace=%s vpn=%s\n" "${config.env.solace.host}" "${config.env.solace.vpn}"
        }
    }

    // 3. Expand this task once per shard from environment.conf.
    // The label gives each expanded task a readable identity: [shard11].
    task "Replay trade messages" for_each="${config.env.blackbird.shards}" label="${item.name}" {
        ssh {
            host "${item.host}"
            user "${config.env.ssh.user}"
        }

        cwd "${item.root}"

        step "Upload order id file" {
            // Step-level override back to local context, executing on this host.
            local {
                cwd "${project.dir}"
            }

            run scp "${input.order_ids_file}" "${config.env.ssh.user}@${item.host}:${item.root}/replay-order-ids.txt"
        }

        step "Unpack archive" {
            run tar -xzf "${item.archive}" -C .
        }

        step "Copy trading logs" {
            shell "cp log/trading/* ."
        }

        step "Repair copied log" {
            shell """
                export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:${config.env.blackbird.solace_ssl_lib}:${config.env.blackbird.native_lib}"
                printf 'open %s --repair --mode rw\nquit\n' "${item.log_file}" | "${config.env.blackbird.tlt}"
                """
        }

        step "Replay selected orders" {
            shell """
                export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:${config.env.blackbird.solace_ssl_lib}:${config.env.blackbird.native_lib}"
                order_ids="$(sed '/^[[:space:]]*$/d' replay-order-ids.txt | sed "s/.*/'&'/" | paste -sd, -)"
                selector="entry.className='com.barclays.eq.roe.salestrading.TradeMessage' and ExecID in ($order_ids)"

                java -cp "${item.app_jar}" \
                    com.barclays.eq.apex.tools.TxnLogRepublisher \
                    --host="${config.env.solace.host}" \
                    --vpn="${config.env.solace.vpn}" \
                    "${item.log_file}" \
                    "$selector"
                """
        }
    }
}
```

Before Flockr runs anything, the runbook expands into named command identities:

```text
Prepare local replay inputs.Check order id file
Prepare local replay inputs.Show target environment
Replay trade messages[shard11].Upload order id file
Replay trade messages[shard11].Unpack archive
Replay trade messages[shard11].Copy trading logs
Replay trade messages[shard11].Repair copied log
Replay trade messages[shard11].Replay selected orders
Replay trade messages[shard12].Upload order id file
...
```

Example result lines:

```text
Prepare local replay inputs.Check order id file: exit=0
Prepare local replay inputs.Show target environment: exit=0
Replay trade messages[shard11].Upload order id file: exit=0
Replay trade messages[shard11].Unpack archive: exit=0
Replay trade messages[shard11].Copy trading logs: exit=0
Replay trade messages[shard11].Repair copied log: exit=0
Replay trade messages[shard11].Replay selected orders: exit=0
```

## 2. Replay A Single Shard With `loggingLevel=DEBUG`

This uses a selected one-shard working set from config:

```kdl
task "Debug logging replay" for_each="${config.env.run.selected_shards}" label="${item.name}" {
    ssh {
        host "${item.host}"
        user "${config.env.ssh.user}"
    }

    cwd "${item.trace_root}"

    step "Clone app root" {
        shell """
            rsync -a \
                --exclude 'data/trading/archive/' \
                --exclude 'log/trading/archive/' \
                "${item.root}/" .
            """
    }

    step "Enable debug logging" {
        shell """
            sed -i.bak \
                -e 's/log.level=ERROR/log.level=DEBUG/g' \
                -e 's/log.level=error/log.level=debug/g' \
                config/environment.conf
            """
    }

    step "Start Blackbird" {
        shell """
            export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:${config.env.blackbird.solace_ssl_lib}:${config.env.blackbird.native_lib}"
            app/trading/bin/start.sh
            """
    }
}
```

The shape stays the same as the all-shard replay: config, selected items,
inherited SSH context, named steps.

## 3. Stage Replay For IDE Step Debugging

This is the same as the single-shard debug replay, with one launch change:

```kdl
step "Start Blackbird suspended" {
    shell """
        export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:${config.env.blackbird.solace_ssl_lib}:${config.env.blackbird.native_lib}"
        export JAVA_TOOL_OPTIONS="$JAVA_TOOL_OPTIONS -agentlib:jdwp=transport=dt_socket,server=y,suspend=y,address=*:${item.debug_port}"
        app/trading/bin/start.sh
        """
}
```

With `suspend=y`, the JVM waits for IntelliJ before startup.

## Verify

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev,hocon]"
.venv/bin/python -m pytest
.venv/bin/python -m ruff check src tests
```
