{
  description = "russellian-book-suite hermetic dev environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
    flake-utils.url = "github:numtide/flake-utils";
    rust-overlay = {
      url = "github:oxalica/rust-overlay";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, rust-overlay }:
    let
      # REQ-CI-043: declare the supported systems as an explicit named
      # constant so the matrix is greppable and the macOS contributor
      # path is documented in source. `eachDefaultSystem` would also
      # cover these, but naming them lets the runbook
      # (docs/operations/ci-platforms.md) point at one location.
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      # `forAllSystems` follows the canonical nixpkgs idiom for
      # per-system attribute construction. It is exposed here so
      # downstream additions (formatter, hydra jobs, custom checks
      # that don't fit eachSystem's mould) can build per-system
      # attrsets via `forAllSystems (system: ...)`.
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    in
    flake-utils.lib.eachSystem supportedSystems (system:
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
          pytest
          pytest-xdist
          ruff
          pyyaml
          jinja2
        ]);
        # Single source of truth for the toolchain — used by both
        # devShells.default and packages.preflight so they stay in sync.
        devPackages = with pkgs; [
          rust
          mold
          sccache
          cargo-nextest
          nodejs_22
          nodePackages.pnpm
          babashka
          python
          jdk21
          clj-kondo
          z3
          cmake
          gnumake
          pkg-config
          lefthook
          git
          gh
          jq
          yq
          curl
          nixpkgs-fmt
        ];
      in
      {
        devShells.default = pkgs.mkShell {
          name = "russellian-book-suite";
          packages = devPackages;

          shellHook = ''
            # RUSTC_WRAPPER=sccache is set externally (by mozilla-actions/sccache-action
            # in CI, or by the dev locally) — not here, so the shell stays usable in
            # environments without GHA Cache (CI jobs that disable sccache, local
            # dev, nightly runs).
            export CARGO_BUILD_RUSTFLAGS="-C link-arg=-fuse-ld=mold"
            export CARGO_INCREMENTAL=0
            export PATH="$HOME/.cargo/bin:$PATH"
            export NBB_PATH="$PWD/.nbb"
            export NIX_CONFIG="experimental-features = nix-command flakes"
          '';
        };

        # `nix build .#preflight` runs `make preflight` with the same
        # toolchain devShells.default provides. CI uses this as a single
        # entry point for drift verification.
        packages.preflight = pkgs.writeShellApplication {
          name = "preflight";
          runtimeInputs = devPackages;
          text = ''
            cd "$PWD"
            make preflight
          '';
        };

        # Flake-level check: assert the makefile preflight target's step list
        # matches scripts/ci-steps.txt. Detects drift between CI YAML and
        # local Makefile.
        checks.flake-drift = pkgs.runCommand "flake-drift-check"
          {
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
