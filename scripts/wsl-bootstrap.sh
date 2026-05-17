#!/usr/bin/env bash
# scripts/wsl-bootstrap.sh — one-shot WSL Ubuntu 24.04 → Nix → direnv setup.
# Idempotent: safe to re-run.
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/work/russellian-book-suite}"
REPO_URL="${REPO_URL:-git@github.com:CharlesHoskinson/russellian-book-suite.git}"

log() { printf '\033[1;34m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m==> %s\033[0m\n' "$*" >&2; }
fail() { printf '\033[1;31m==> %s\033[0m\n' "$*" >&2; exit 1; }

# 1. Sanity: WSL2 + Ubuntu
if [ ! -r /proc/version ] || ! grep -qi microsoft /proc/version; then
  warn "Not running inside WSL; continuing anyway (macOS/Linux path)."
fi
if [ ! -f /etc/os-release ] || ! grep -q '^ID=ubuntu' /etc/os-release; then
  warn "Not Ubuntu; some apt commands may differ."
fi

# 2. apt prerequisites
log "Installing apt prerequisites…"
sudo apt-get update -qq
sudo apt-get install -y -qq curl ca-certificates git direnv build-essential

# 3. Nix via Determinate Systems installer
if ! command -v nix >/dev/null 2>&1; then
  log "Installing Nix (Determinate Systems installer)…"
  curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix |
    sh -s -- install linux --extra-conf "trusted-users = $(whoami)" --no-confirm
  # shellcheck disable=SC1091
  source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh
else
  log "Nix already installed: $(nix --version)"
fi

# 4. direnv hook
if ! grep -q 'direnv hook bash' ~/.bashrc 2>/dev/null; then
  log "Wiring direnv into ~/.bashrc…"
  echo 'eval "$(direnv hook bash)"' >> ~/.bashrc
fi
mkdir -p ~/.config/direnv
if [ ! -f ~/.config/direnv/direnvrc ]; then
  echo 'source $HOME/.nix-profile/share/nix-direnv/direnvrc' > ~/.config/direnv/direnvrc
fi

# 5. Clone repo (if absent)
if [ ! -d "$REPO_DIR" ]; then
  log "Cloning $REPO_URL → $REPO_DIR…"
  mkdir -p "$(dirname "$REPO_DIR")"
  git clone "$REPO_URL" "$REPO_DIR"
else
  log "Repo already cloned at $REPO_DIR"
fi

# 6. Git defaults
log "Setting git defaults (autocrlf=false, eol=lf)…"
git config --global core.autocrlf false
git config --global core.eol lf

# 7. Final message
cat <<EOF

✅ WSL bootstrap complete.

Next steps:
  cd $REPO_DIR
  direnv allow            # one-time; Nix downloads toolchain on first entry
  make preflight          # green ⇒ ready to ship

If make preflight fails on the first run, check:
  nix --version           # should report Determinate Nix
  nix develop -c rustc --version  # should report 1.90.x
  echo \$NIX_PATH         # should mention nixpkgs

EOF
