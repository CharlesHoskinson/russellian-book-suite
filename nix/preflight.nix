# `nix build .#preflight` wraps `make preflight` with the full toolchain —
# the nightly's drift probe that the packaged toolchain and the Makefile
# agree.
{ ... }:
{
  perSystem = { pkgs, toolchains, ... }: {
    packages.preflight = pkgs.writeShellApplication {
      name = "preflight";
      runtimeInputs = toolchains.rust ++ toolchains.python ++ toolchains.cljs ++ toolchains.core;
      text = ''
        cd "$PWD"
        make preflight
      '';
    };
  };
}
