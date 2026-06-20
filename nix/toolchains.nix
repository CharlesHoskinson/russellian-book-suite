# Toolchain package sets — the single source for what each language stack
# needs. Consumed by shells.nix, checks.nix, and preflight.nix via the
# `toolchains` module arg.
{ inputs, ... }:
{
  perSystem = { system, pkgs, ... }: {
    # rust-overlay must be visible to every module's `pkgs`.
    _module.args.pkgs = import inputs.nixpkgs {
      inherit system;
      overlays = [ inputs.rust-overlay.overlays.default ];
    };

    _module.args.toolchains = rec {
      rustToolchain = pkgs.rust-bin.stable."1.90.0".default.override {
        extensions = [ "rust-src" "clippy" "rustfmt" ];
      };
      # Python + the few PyPI deps the booklogic build needs at the system
      # level (everything else lives in per-skill venvs).
      pythonEnv = pkgs.python313.withPackages (ps: with ps; [
        pytest
        pytest-xdist
        ruff
        pyyaml
        jinja2
        psutil
      ]);
      rust = [ rustToolchain pkgs.sccache pkgs.cargo-nextest pkgs.z3 pkgs.cmake pkgs.pkg-config ]
        # mold is linux-only (marked broken on darwin in nixpkgs 25.05); darwin
        # uses the default ld64.
        ++ pkgs.lib.optionals pkgs.stdenv.hostPlatform.isLinux [ pkgs.mold ];
      python = [ pythonEnv ];
      cljs = [ pkgs.nodejs_22 pkgs.pnpm pkgs.babashka pkgs.jdk21 pkgs.clj-kondo ];
      core = [ pkgs.git pkgs.gh pkgs.jq pkgs.yq pkgs.curl pkgs.gnumake pkgs.lefthook pkgs.nixpkgs-fmt ];
    };
  };
}
