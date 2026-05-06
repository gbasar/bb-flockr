---
name: flockr-e2e
description: Run the flockr end-to-end Docker Compose test suite. Use when verifying the full stack before a merge or release.
allowed-tools: Bash, Read
---

Run the flockr e2e test suite using `scripts/dev.sh`.

## Steps

1. Confirm Docker is running:
   ```bash
   docker info >/dev/null 2>&1 || echo "Docker is not running"
   ```

2. Run the full e2e suite (builds images, starts compose, runs runbook inside the CNC container, tears down):
   ```bash
   cd /Users/gregb/devhome/flockr && scripts/dev.sh e2e
   ```

3. Report results:
   - If the flockr command inside the container exits 0: PASS
   - If any step fails (docker build, compose up, exec, flockr exit code): STOP and show exactly what failed
   - Do NOT proceed to merge or push if e2e fails

## What the e2e does
- Builds `flockr-fedora-cnc` (the command-and-control container with flockr installed) and `flockr-fedora-shard-a/b` (SSH targets)
- Starts a `config-web` container serving `environment.conf` over HTTP
- Runs `flockr -vv run tests/e2e/docker-ssh-runbook.kdl --config envConf=http://config-web/environment.conf` inside the CNC container
- Tears down the compose stack and volumes when done

## Shortcut for full verification (lint + unit tests + e2e):
```bash
cd /Users/gregb/devhome/flockr && scripts/dev.sh full
```
