# Per-language dev shells plus the composed default. A Python-skill
# contributor uses `nix develop .#python` and skips the rust/JDK closure.
{ ... }:
{
  perSystem = { pkgs, lib, config, toolchains, lefthookHooks, ... }:
    let
      # One install command per hook in nix/hooks.nix — adding a hook there
      # (e.g. commit-msg) installs it here automatically; no second list.
      # $GIT_HOOKS is resolved via git so this works in worktrees too.
      installHooks = lib.concatMapStringsSep "\n"
        (hook: ''
          printf '%s\n' '#!/bin/sh' 'exec ${pkgs.lefthook}/bin/lefthook run "${hook}" "$@"' > "$GIT_HOOKS/${hook}"
          chmod +x "$GIT_HOOKS/${hook}"
        '')
        lefthookHooks;
      # Whitelist of hooks we own, for the stale-sweep `case` — derived from
      # lefthookHooks so there is no second list to drift.
      knownHooksCase = lib.concatMapStringsSep "|" (h: h) lefthookHooks;
      baseHook = ''
        export NBB_PATH="$PWD/.nbb"
        export NIX_CONFIG="experimental-features = nix-command flakes"
        # lefthook.yml is generated from nix/hooks.nix (gitignored).
        # Hook scripts pin the lefthook store path directly, so hooks fire
        # correctly from any terminal (Linux/WSL only — Windows-side git
        # never runs these). Paths resolve through git for worktree support.
        GIT_HOOKS="$(git rev-parse --git-path hooks 2>/dev/null || true)"
        TOPLEVEL="$(git rev-parse --show-toplevel 2>/dev/null || true)"
        if [ -n "$GIT_HOOKS" ] && [ -n "$TOPLEVEL" ]; then
          if [ "$(readlink "$TOPLEVEL/lefthook.yml" 2>/dev/null)" != "${config.packages.lefthook-config}" ]; then
            ln -sf ${config.packages.lefthook-config} "$TOPLEVEL/lefthook.yml"
          fi
          mkdir -p "$GIT_HOOKS"
          ${installHooks}
          # Sweep stale lefthook-era hooks (e.g. prepare-commit-msg from a
          # prior `lefthook install`). Only touch files that mention lefthook
          # and are not ones we generate; user-custom hooks stay untouched.
          for f in "$GIT_HOOKS"/*; do
            [ -f "$f" ] || continue
            case "$(basename "$f")" in
              ${knownHooksCase}) continue ;;
            esac
            if grep -q lefthook "$f" 2>/dev/null; then
              rm -f "$f"
            fi
          done
        fi
      '';
      # RUSTC_WRAPPER=sccache is set externally (CI or dev), not here — the
      # shell stays usable in environments without GHA Cache.
      rustHook = ''
        export CARGO_INCREMENTAL=0
        export PATH="$HOME/.cargo/bin:$PATH"
      '' + pkgs.lib.optionalString pkgs.stdenv.hostPlatform.isLinux ''
        export CARGO_BUILD_RUSTFLAGS="-C link-arg=-fuse-ld=mold"
        # z3 splits bin/lib outputs; the z3 crate links libz3 dynamically but rustc
        # records no RPATH for the pkg-config -L dir, so the lib output must be on
        # LD_LIBRARY_PATH for the loader. (darwin resolves via absolute install_names.)
        export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [ pkgs.z3.lib ]}''${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
      '';
    in
    {
      devShells.rust = pkgs.mkShell {
        name = "russellian-book-suite-rust";
        packages = toolchains.rust ++ toolchains.core;
        shellHook = baseHook + rustHook;
      };
      devShells.python = pkgs.mkShell {
        name = "russellian-book-suite-python";
        packages = toolchains.python ++ toolchains.core;
        shellHook = baseHook;
      };
      devShells.cljs = pkgs.mkShell {
        name = "russellian-book-suite-cljs";
        packages = toolchains.cljs ++ toolchains.core;
        shellHook = baseHook;
      };
      # Explicit concat rather than inputsFrom: identical package set, no
      # triplicated shell hooks.
      devShells.default = pkgs.mkShell {
        name = "russellian-book-suite";
        packages = toolchains.rust ++ toolchains.python ++ toolchains.cljs ++ toolchains.core;
        shellHook = baseHook + rustHook;
      };
    };
}
