#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

usage() {
    cat <<'USAGE'
Usage:
  scripts/dev.sh <command> [--tool uv|pip]

Commands:
  setup    Create .venv and install runtime + dev dependencies
  test     Run pytest
  e2e      Run Docker Compose end-to-end tests
  full     Run lint, pytest, and Docker Compose end-to-end tests
  lab      Start Docker SSH targets for host-side manual runbook testing
  lab-down Stop the Docker SSH lab
  lint     Run ruff
  build    Build wheel/sdist into dist/
  context  Write a source/context dump for restricted AI agents
  docker-key
           Generate a local Docker SSH test key

Tool selection:
  Defaults to uv when available, otherwise pip.
  Override with --tool uv or --tool pip.

Context options:
  --output PATH   Output file. Defaults to build/context/source-context.txt.
USAGE
}

command="${1:-}"
if [[ -z "$command" || "$command" == "-h" || "$command" == "--help" ]]; then
    usage
    exit 0
fi
shift

tool=""
context_output=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tool)
            tool="${2:-}"
            shift 2
            ;;
        --tool=*)
            tool="${1#--tool=}"
            shift
            ;;
        --output)
            context_output="${2:-}"
            shift 2
            ;;
        --output=*)
            context_output="${1#--output=}"
            shift
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ -z "$tool" ]]; then
    if command -v uv >/dev/null 2>&1; then
        tool="uv"
    else
        tool="pip"
    fi
fi

if [[ "$tool" != "uv" && "$tool" != "pip" ]]; then
    echo "Unsupported tool: $tool" >&2
    usage >&2
    exit 2
fi

python_bin() {
    if command -v python3.12 >/dev/null 2>&1; then
        echo "python3.12"
    else
        echo "python3"
    fi
}

venv_python() {
    echo "$VENV_DIR/bin/python"
}

setup_with_pip() {
    local python
    python="$(python_bin)"

    "$python" -m venv "$VENV_DIR"
    "$(venv_python)" -m pip install --upgrade pip
    "$(venv_python)" -m pip install -e "$ROOT_DIR[dev]"
}

setup_with_uv() {
    local python
    python="$(python_bin)"

    uv venv --python "$python" "$VENV_DIR"
    uv pip install --python "$(venv_python)" -e "$ROOT_DIR[dev]"
}

ensure_venv() {
    if [[ ! -x "$(venv_python)" ]]; then
        echo ".venv is missing. Run: scripts/dev.sh setup --tool $tool" >&2
        exit 1
    fi
}

write_section() {
    local title="$1"
    local output="$2"

    {
        echo
        echo "================================================================================"
        echo "$title"
        echo "================================================================================"
        echo
    } >> "$output"
}

append_command_output() {
    local title="$1"
    local output="$2"
    shift 2

    write_section "$title" "$output"
    {
        echo "\$ $*"
        "$@" 2>&1 || true
    } >> "$output"
}

append_file() {
    local file="$1"
    local output="$2"

    write_section "FILE: $file" "$output"
    cat "$ROOT_DIR/$file" >> "$output"
}

context_files() {
    {
        find . -maxdepth 1 -type f \( -name "README.md" -o -name "pyproject.toml" -o -name "flockr.kdl" \)
        find docker examples scripts src tests -type f \
            ! -path "*/__pycache__/*" \
            ! -name "*.pyc"
        find project-docs -maxdepth 1 -type f \
            ! -name "vibe-coding-transcript.md"
    } | sed 's#^\./##' | sort
}

write_context_dump() {
    local output="${context_output:-$ROOT_DIR/build/context/source-context.txt}"
    local output_dir
    output_dir="$(dirname "$output")"

    mkdir -p "$output_dir"
    : > "$output"

    append_command_output "REPO" "$output" pwd
    append_command_output "GIT STATUS" "$output" git status --short
    append_command_output "RECENT COMMITS" "$output" git log --oneline --decorate -5
    append_command_output "PYTHON" "$output" "$(python_bin)" --version
    append_command_output "PIP" "$output" "$(python_bin)" -m pip --version

    if [[ -x "$(venv_python)" ]]; then
        append_command_output "VENV PYTHON" "$output" "$(venv_python)" --version
        if "$(venv_python)" -m pip --version >/dev/null 2>&1; then
            append_command_output "VENV PACKAGES" "$output" "$(venv_python)" -m pip freeze
        else
            write_section "VENV PACKAGES" "$output"
            echo ".venv exists, but pip is not installed in it" >> "$output"
        fi
    else
        write_section "VENV PACKAGES" "$output"
        echo ".venv not found" >> "$output"
    fi

    write_section "SOURCE FILE LISTING" "$output"
    while IFS= read -r file; do
        ls -l "$ROOT_DIR/$file" >> "$output"
    done < <(context_files)

    while IFS= read -r file; do
        append_file "$file" "$output"
    done < <(context_files)

    echo "Wrote context dump: $output"
}

generate_docker_key() {
    local key_dir="$ROOT_DIR/.docker/ssh"
    local key_file="$key_dir/id_ed25519"

    mkdir -p "$key_dir"

    if [[ ! -f "$key_file" ]]; then
        ssh-keygen -t ed25519 -N "" -f "$key_file" -C "flockr-docker-test"
    fi

    cp "$key_file.pub" "$ROOT_DIR/docker/ssh-target/authorized_keys"
    echo "Wrote Docker SSH public key: docker/ssh-target/authorized_keys"
    echo "Private key stays local and ignored: .docker/ssh/id_ed25519"
}

run_e2e() {
    local compose_file="$ROOT_DIR/tests/e2e/docker-compose.yaml"
    local replay_output
    local debug_output

    docker info >/dev/null
    generate_docker_key
    docker compose -f "$compose_file" up -d --build
    trap "docker compose -f '$compose_file' down -v" RETURN

    replay_output="$(
        docker compose -f "$compose_file" exec -T flockr-fedora-cnc \
            flockr -vv run tests/e2e/replay-runbook.kdl \
            --config envConf=http://config-web/environment.conf
    )"
    echo "$replay_output"
    grep -F "replay[shard-a].run-replay: exit=0" <<< "$replay_output" >/dev/null
    grep -F "replay.tradeIds=TRADE-1" <<< "$replay_output" >/dev/null
    grep -F "TRADE-2" <<< "$replay_output" >/dev/null

    debug_output="$(
        docker compose -f "$compose_file" exec -T flockr-fedora-cnc \
            flockr -vv run tests/e2e/debug-runbook.kdl \
            --config envConf=http://config-web/environment.conf
    )"
    echo "$debug_output"
    grep -F "debug logging replay[shard11].Enable debug logging: exit=0" <<< "$debug_output" >/dev/null
    grep -F "blackbird.level=DEBUG" <<< "$debug_output" >/dev/null
    grep -F "DEBUG loaded inbound transaction log" <<< "$debug_output" >/dev/null
}

lab_compose_args() {
    echo -f "$ROOT_DIR/tests/e2e/docker-compose.yaml" -f "$ROOT_DIR/tests/e2e/docker-compose.lab.yaml"
}

lab_port() {
    local service="$1"
    local endpoint

    endpoint="$(docker compose $(lab_compose_args) port "$service" 22)"
    echo "${endpoint##*:}"
}

write_lab_config() {
    local output_dir="$ROOT_DIR/build/lab"
    local output_file="$output_dir/environment.kdl"
    local shard_a_port
    local shard_b_port

    shard_a_port="$(lab_port flockr-fedora-shard-a)"
    shard_b_port="$(lab_port flockr-fedora-shard-b)"

    mkdir -p "$output_dir"
    {
        echo "deploy {"
        echo "    instances {"
        echo "        item name=\"shard-a\" host=\"localhost\" port=\"$shard_a_port\" login=\"flockr\" base_dir=\"/apps/flockr\" identity_file=\"$ROOT_DIR/.docker/ssh/id_ed25519\""
        echo "        item name=\"shard-b\" host=\"localhost\" port=\"$shard_b_port\" login=\"flockr\" base_dir=\"/apps/flockr\" identity_file=\"$ROOT_DIR/.docker/ssh/id_ed25519\""
        echo "    }"
        echo "}"
    } > "$output_file"

    echo "Wrote lab config: build/lab/environment.kdl"
    echo
    echo "Try a runbook from your host Python with:"
    echo "  .venv/bin/python -m flockr.cli -vv run examples/docker-ssh-runbook.kdl --config envConf=build/lab/environment.kdl"
    echo
    echo "Stop the lab with:"
    echo "  scripts/dev.sh lab-down"
}

run_lab() {
    docker info >/dev/null
    generate_docker_key
    docker compose $(lab_compose_args) up -d --build flockr-fedora-shard-a flockr-fedora-shard-b
    write_lab_config
}

run_lab_down() {
    docker compose $(lab_compose_args) down -v
}


run_full() {
    ensure_venv
    "$(venv_python)" -m ruff check src tests
    "$(venv_python)" -m pytest
    run_e2e
}

case "$command" in
    setup)
        if [[ "$tool" == "uv" ]]; then
            setup_with_uv
        else
            setup_with_pip
        fi
        ;;
    test)
        ensure_venv
        "$(venv_python)" -m pytest
        ;;
    e2e)
        run_e2e
        ;;
    full)
        run_full
        ;;
    lab)
        run_lab
        ;;
    lab-down)
        run_lab_down
        ;;
    lint)
        ensure_venv
        "$(venv_python)" -m ruff check src tests
        ;;
    build)
        ensure_venv
        "$(venv_python)" -m build
        ;;
    context)
        write_context_dump
        ;;
    docker-key)
        generate_docker_key
        ;;
    *)
        echo "Unknown command: $command" >&2
        usage >&2
        exit 2
        ;;
esac
