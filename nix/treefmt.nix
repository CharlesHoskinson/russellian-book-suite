# Formatter/linter declarations — one definition feeds `nix fmt`
# (flakeFormatter) and `checks.formatting` (flakeCheck), both defaults
# of the treefmt-nix flake module. ruff reads ruff.toml at the repo root;
# treefmt runs from projectRootFile's directory, so discovery is automatic.
{ ... }:
{
  perSystem = { ... }: {
    treefmt = {
      projectRootFile = "flake.nix";
      programs.nixpkgs-fmt.enable = true;
      programs.rustfmt.enable = true;
      programs.rustfmt.edition = "2024";
      programs.ruff-check.enable = true;
      settings.global.excludes = [ "examples/**" ];
    };
  };
}
