# Architecture Trash Bin

Decisions that were considered, written up, and then abandoned or superseded. Kept here for reference.

---

## Project Identity — Interactive First-Run (Abandoned)

**Original idea:** If flockr starts without a resolvable project context, prompt the user to specify one. Write the answer to `~/.config/flockr/state.kdl`. Subsequent runs load from state automatically — analogous to `kubectl` context.

**Why abandoned:** Adds complexity before the simpler approach (`project.name` = basename of cwd) has been proven insufficient. Deferred indefinitely.

---

## SSH via asyncssh (Rejected)

**Original idea:** Use `asyncssh` for SSH execution — async-native, actively maintained, no subprocess overhead.

**Why rejected:** Shelling out to the local `ssh` binary via `asyncio.create_subprocess_exec` inherits `~/.ssh/config`, keys, proxy jumps, and agent forwarding for free. `asyncssh` would require reimplementing all of that. Subprocess wins on simplicity.

---

## YAML — "Fully Supported" (Never Built)

**Original claim:** YAML listed as fully supported and used in integration tests.

**Reality:** Never implemented. The extension map in `config/load.py` makes it trivially addable when there's a real use case, but there isn't one yet.
