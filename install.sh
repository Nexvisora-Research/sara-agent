#!/usr/bin/env bash
# Sara Agent one-line installer.
#
# Usage:
#   curl -fsSL https://your-domain/install.sh | bash
#
# Options:
#   SARA_REPO_URL=https://github.com/NexvisoraResearch/sara-agent.git
#   SARA_INSTALL_DIR=~/.sara/sara-agent
#   SARA_BRANCH=main
#   SARA_COMMAND_NAME=sara
#   SARA_RUN_SETUP=1

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

REPO_URL="${SARA_REPO_URL:-https://github.com/NexvisoraResearch/sara-agent.git}"
BRANCH="${SARA_BRANCH:-main}"
COMMAND_NAME="${SARA_COMMAND_NAME:-sara}"
RUN_SETUP="${SARA_RUN_SETUP:-1}"

log() {
    printf "%b\n" "${CYAN}->${NC} $*"
}

ok() {
    printf "%b\n" "${GREEN}✓${NC} $*"
}

warn() {
    printf "%b\n" "${YELLOW}⚠${NC} $*"
}

die() {
    printf "%b\n" "${RED}✗${NC} $*" >&2
    exit 1
}

have() {
    command -v "$1" >/dev/null 2>&1
}

is_termux() {
    [ -n "${TERMUX_VERSION:-}" ] || [[ "${PREFIX:-}" == *"com.termux/files/usr"* ]]
}

is_wsl() {
    grep -qi microsoft /proc/version 2>/dev/null || grep -qi microsoft /proc/sys/kernel/osrelease 2>/dev/null
}

os_name() {
    if is_termux; then
        printf "termux"
    elif is_wsl; then
        printf "wsl"
    else
        uname -s | tr '[:upper:]' '[:lower:]'
    fi
}

require_supported_os() {
    case "$(os_name)" in
        linux|darwin|wsl|termux) ;;
        *) die "Unsupported OS. Use Linux, macOS, WSL, or Termux." ;;
    esac
}

validate_command_name() {
    case "$COMMAND_NAME" in
        ""|*/*|*:*|*[$'\t\n\r ']*)
            die "Invalid SARA_COMMAND_NAME: $COMMAND_NAME"
            ;;
    esac
}

default_install_dir() {
    if [ "$(id -u)" -eq 0 ] && ! is_termux; then
        printf "/usr/local/lib/sara-agent"
    else
        printf "%s/.sara/sara-agent" "$HOME"
    fi
}

run_sudo() {
    if [ "$(id -u)" -eq 0 ]; then
        "$@"
    elif have sudo; then
        sudo "$@"
    else
        die "This step needs elevated privileges. Install sudo or run the installer with root permissions."
    fi
}

install_packages() {
    log "Installing system dependencies for $(os_name)..."

    if is_termux; then
        pkg update -y
        pkg install -y git python nodejs ffmpeg curl clang make pkg-config openssl
        ok "Termux packages installed"
        return
    fi

    if have apt-get; then
        run_sudo apt-get update
        run_sudo apt-get install -y git python3 python3-venv python3-pip nodejs npm ffmpeg curl ca-certificates build-essential
    elif have dnf; then
        run_sudo dnf install -y git python3 python3-pip nodejs npm ffmpeg curl gcc gcc-c++ make
    elif have pacman; then
        run_sudo pacman -Sy --needed --noconfirm git python nodejs npm ffmpeg curl base-devel
    elif have zypper; then
        run_sudo zypper install -y git python3 python3-pip nodejs npm ffmpeg curl gcc gcc-c++ make
    elif have apk; then
        run_sudo apk add --no-cache git python3 py3-pip nodejs npm ffmpeg curl build-base
    elif have brew; then
        brew update
        brew install git python node ffmpeg curl
    else
        die "No supported package manager found. Install git, Python 3.11+, Node.js, ffmpeg, and curl manually, then rerun."
    fi

    ok "System dependencies installed"
}

install_uv() {
    if is_termux; then
        warn "Skipping uv bootstrap on Termux; the in-repo setup uses python -m venv for Android compatibility."
        return
    fi

    if have uv; then
        ok "uv found ($(uv --version 2>/dev/null || printf unknown))"
        return
    fi

    log "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    have uv || die "uv installed but is not on PATH. Add ~/.local/bin to PATH and rerun."
    ok "uv installed ($(uv --version 2>/dev/null || printf unknown))"
}

clone_or_update_repo() {
    INSTALL_DIR="${SARA_INSTALL_DIR:-$(default_install_dir)}"
    log "Preparing Sara Agent at $INSTALL_DIR..."
    mkdir -p "$(dirname "$INSTALL_DIR")"

    if [ -d "$INSTALL_DIR/.git" ]; then
        log "Existing repo found; updating $BRANCH..."
        git -C "$INSTALL_DIR" fetch --depth 1 origin "$BRANCH"
        git -C "$INSTALL_DIR" checkout "$BRANCH"
        git -C "$INSTALL_DIR" reset --hard "origin/$BRANCH"
    elif [ -e "$INSTALL_DIR" ]; then
        die "$INSTALL_DIR exists but is not a git checkout. Move it aside or set SARA_INSTALL_DIR."
    else
        git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
    fi

    ok "Repository ready"
}

run_repo_setup() {
    INSTALL_DIR="${SARA_INSTALL_DIR:-$(default_install_dir)}"
    log "Creating virtual environment, installing Python packages, and wiring commands..."
    cd "$INSTALL_DIR"

    if [ ! -f "./setup-sara.sh" ]; then
        die "setup-sara.sh was not found in $INSTALL_DIR"
    fi

    chmod +x ./setup-sara.sh
    if [ -r /dev/tty ]; then
        SARA_COMMAND_NAME="$COMMAND_NAME" SARA_RUN_SETUP="$RUN_SETUP" ./setup-sara.sh < /dev/tty
    else
        warn "No interactive terminal detected; skipping setup wizard prompts."
        SARA_COMMAND_NAME="$COMMAND_NAME" SARA_RUN_SETUP=0 ./setup-sara.sh
    fi
}

finish_message() {
    INSTALL_DIR="${SARA_INSTALL_DIR:-$(default_install_dir)}"
    printf "\n%b\n\n" "${GREEN}Sara Agent installation complete.${NC}"
    printf "Command: %s\n" "$COMMAND_NAME"
    printf "Repo:    %s\n" "$INSTALL_DIR"
    printf "\n"
    printf "Try:\n"
    printf "  %s doctor\n" "$COMMAND_NAME"
    printf "  %s\n" "$COMMAND_NAME"

    if [ "$RUN_SETUP" != "1" ]; then
        printf "\nSetup wizard was skipped. Run it later with:\n"
        printf "  %s setup\n" "$COMMAND_NAME"
    fi
}

main() {
    printf "\n%b\n\n" "${CYAN}Sara Agent Installer${NC}"

    require_supported_os
    validate_command_name
    install_packages
    install_uv
    clone_or_update_repo

    run_repo_setup

    finish_message
}

main "$@"
