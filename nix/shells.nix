# Per-language dev shells plus the composed default. A Python-skill
# contributor uses `nix develop .#python` and skips the rust/JDK closure.
{ ... }:
{
  perSystem = { pkgs, toolchains, ... }:
    let
      baseHook = ''
        export NBB_PATH="$PWD/.nbb"
        export NIX_CONFIG="experimental-features = nix-command flakes"
      '';
      # RUSTC_WRAPPER=sccache is set externally (CI or dev), not here — the
      # shell stays usable in environments without GHA Cache.
      rustHook = ''
        export CARGO_BUILD_RUSTFLAGS="-C link-arg=-fuse-ld=mold"
        export CARGO_INCREMENTAL=0
        export PATH="$HOME/.cargo/bin:$PATH"
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
