{
  description = "russellian-book-suite hermetic dev environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
    flake-parts.url = "github:hercules-ci/flake-parts";
    rust-overlay = {
      url = "github:oxalica/rust-overlay";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    treefmt-nix = {
      url = "github:numtide/treefmt-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = inputs@{ flake-parts, ... }:
    let
      # REQ-CI-043: the supported systems stay a named, greppable constant;
      # the runbook (docs/operations/ci-platforms.md) points here.
      supportedSystems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
    in
    flake-parts.lib.mkFlake { inherit inputs; } {
      systems = supportedSystems;
      imports = [
        inputs.treefmt-nix.flakeModule
        ./nix/toolchains.nix
        ./nix/shells.nix
        ./nix/treefmt.nix
        ./nix/hooks.nix
        ./nix/checks.nix
        ./nix/preflight.nix
      ];
    };
}
