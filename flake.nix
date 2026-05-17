{
  description = "russellian-book-suite hermetic dev environment";

  inputs = {
    nixpkgs.url      = "github:NixOS/nixpkgs/nixos-25.05";
    flake-utils.url  = "github:numtide/flake-utils";
    rust-overlay = {
      url = "github:oxalica/rust-overlay";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, rust-overlay }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ rust-overlay.overlays.default ];
        };
        rust = pkgs.rust-bin.stable."1.90.0".default.override {
          extensions = [ "rust-src" "clippy" "rustfmt" ];
        };
        # Python + the few PyPI deps that the booklogic build truly needs at
        # the system level (everything else lives in per-skill venvs).
        python = pkgs.python313.withPackages (ps: with ps; [
          pytest pytest-xdist ruff pyyaml jinja2
        ]);
      in {
        devShells.default = pkgs.mkShell {
          name = "russellian-book-suite";
          packages = with pkgs; [
            # Rust
            rust
            mold sccache cargo-nextest
            # Node / CLJS
            nodejs_22 nodePackages.pnpm babashka
            # Python
            python
            # JVM (for shadow-cljs)
            jdk21 clj-kondo
            # SMT
            z3
            # Build essentials
            cmake gnumake pkg-config
            # Git hooks + automation
            lefthook git gh
            # Bootstrap utilities
            jq yq curl
          ];

          shellHook = ''
            export RUSTC_WRAPPER=sccache
            export CARGO_BUILD_RUSTFLAGS="-C link-arg=-fuse-ld=mold"
            export CARGO_INCREMENTAL=0
            export PATH="$HOME/.cargo/bin:$PATH"
            export NBB_PATH="$PWD/.nbb"
            # Cachix uses these to skip rebuild on the runner
            export NIX_CONFIG="experimental-features = nix-command flakes"
          '';
        };

        # `nix build .#preflight` runs `make preflight` inside the shell.
        # CI uses this as a single entry point for drift verification.
        packages.preflight = pkgs.writeShellApplication {
          name = "preflight";
          runtimeInputs = [ pkgs.gnumake ];
          text = ''
            cd "$PWD"
            make preflight
          '';
        };

        # Flake-level check: assert the makefile preflight target's step list
        # matches scripts/ci-steps.txt. Detects drift between CI YAML and
        # local Makefile.
        checks.flake-drift = pkgs.runCommand "flake-drift-check" {
          buildInputs = [ pkgs.gnumake pkgs.coreutils ];
        } ''
          if ! diff -q ${./scripts/ci-steps.txt} <(make -C ${./.} -n preflight | grep -E '^\t' | sed 's/^\t//') >/dev/null 2>&1; then
            echo "DRIFT: scripts/ci-steps.txt diverges from Makefile preflight"
            diff ${./scripts/ci-steps.txt} <(make -C ${./.} -n preflight | grep -E '^\t' | sed 's/^\t//') || true
            exit 1
          fi
          touch $out
        '';
      });
}
