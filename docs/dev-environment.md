# Developer Environment Setup

This repo's CI runs on Ubuntu Linux. To eliminate "works on my machine" drift, Windows developers run their builds inside WSL2 Ubuntu 24.04 with a Nix-pinned toolchain. macOS and Linux developers skip WSL and run Nix directly.

## TL;DR

1. Install WSL2 + Ubuntu 24.04 (Windows only)
2. Install Nix via the Determinate Systems installer
3. `git clone https://github.com/CharlesHoskinson/russellian-book-suite ~/work/russellian-book-suite`
4. `cd ~/work/russellian-book-suite && direnv allow`
5. `make preflight`

Green preflight ⇒ green CI. Always.

## Why WSL2

GitHub Actions runs on `ubuntu-24.04`. Compiled artifacts (`.so` libraries, the napi `.node` addon, Z3-linked binaries) only exercise the Linux ABI on Linux. Sprint 5 burned 60 minutes of wall time on bugs that surfaced only in CI because no Windows developer could build a `.so` locally. WSL2 closes that gap.

## Setup — Windows 11

### 1. Install WSL2 + Ubuntu 24.04

Open PowerShell as Administrator:

```powershell
wsl --install -d Ubuntu-24.04
```

Restart when prompted. On first launch, set a Linux username and password.

Confirm:

```powershell
wsl --status
# Default Distribution: Ubuntu-24.04
# Default Version: 2
```

### 2. Drop `.wslconfig` in your Windows home directory

Copy `.wslconfig.example` from this repo to `%USERPROFILE%\.wslconfig` and edit the `memory` and `processors` lines to fit your hardware. After editing, run `wsl --shutdown` once so the new config takes effect.

### 3. Install Nix in WSL

Inside WSL Ubuntu:

```bash
curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install linux \
    --extra-conf "trusted-users = $(whoami)" \
    --no-confirm
```

After install, restart the shell (`exec $SHELL`). Confirm:

```bash
nix --version
# nix (Determinate Nix) 2.x.x
```

### 4. Install direnv + nix-direnv

```bash
sudo apt-get update && sudo apt-get install -y direnv
mkdir -p ~/.config/direnv
echo 'source $HOME/.nix-profile/share/nix-direnv/direnvrc' > ~/.config/direnv/direnvrc
echo 'eval "$(direnv hook bash)"' >> ~/.bashrc
exec bash
```

### 5. Configure git

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global core.autocrlf false
git config --global core.eol lf
git config --global credential.helper \
  "/mnt/c/Program\ Files/Git/mingw64/bin/git-credential-manager.exe"
```

The credential-helper line bridges Windows' Git Credential Manager into WSL so HTTPS pushes use your existing credential vault.

For SSH access, generate a fresh key inside WSL and paste the public half into GitHub:

```bash
ssh-keygen -t ed25519 -C "you@example.com"
cat ~/.ssh/id_ed25519.pub
# Paste into https://github.com/settings/keys
```

### 6. Clone and bootstrap the repo

```bash
mkdir -p ~/work
cd ~/work
git clone git@github.com:CharlesHoskinson/russellian-book-suite.git
cd russellian-book-suite
direnv allow
# Nix downloads the toolchain on first entry; subsequent shells are instant.
```

### 7. Run pre-flight

```bash
make preflight
# Expected: green; same command CI runs.
```

### 8. Install lefthook git hooks

```bash
lefthook install
# Installs .git/hooks/{pre-commit,pre-push}.
```

## Setup — macOS / Linux

Skip WSL. Steps 3-7 above apply directly.

## Open the repo in VS Code

From Windows VS Code, install the **Remote - WSL** extension, then:

```bash
# from inside WSL, at the repo root:
code .
```

Files appear local to VS Code; the integrated terminal opens inside WSL with the Nix shell loaded. Native filesystem watches work.

## Recover from a corrupted WSL distro

```powershell
wsl --shutdown
wsl --export Ubuntu-24.04 D:\backups\ubuntu-2026-05-17.tar
# weekly cadence is enough; restore with:
wsl --import Ubuntu-restored C:\WSL\Ubuntu-restored D:\backups\ubuntu-2026-05-17.tar
```

Repo work-in-progress should always be pushed to a personal fork branch — that way `wsl --import` only loses uncommitted changes.

## Daily commands

| What you want | Command |
|---|---|
| Enter Nix shell explicitly | `nix develop` |
| Run the same gate CI runs | `make preflight` |
| Run only the changed-files gate | lefthook does this automatically on `git commit` and `git push` |
| Update Nix toolchain | `nix flake update` then commit `flake.lock` |
| Drop into a one-off Python | `nix shell nixpkgs#python313` |
| Inspect what's in the shell | `nix develop -c env | grep -E 'PATH|RUSTC'` |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `direnv: error /path/.envrc is blocked` | `direnv allow` once per repo |
| Slow `cargo build` / `git status` | You are on `/mnt/c/...`. Move the repo to `~/work/...` (ext4) |
| `wsl: command not found` from PowerShell | Reboot after `wsl --install` |
| HTTPS push prompts for password every time | Re-run the `git config credential.helper` line in step 5 |
| `.node` addon fails to load | Confirm you ran `make preflight` (or `npm run build`) — the `.node` only exists after `build:rust` |
