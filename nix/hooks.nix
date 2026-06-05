# Hook definitions. One attrset renders lefthook's config; hook commands are
# pinned to the same store paths the flake checks use, so the pre-commit
# surface and CI cannot drift. The rendered file is .gitignored; the dev
# shell refreshes the lefthook.yml symlink on entry.
# readme-lint is hook-only (tools/readme-lint/.venv is sandbox-unsafe).
# pre-push keeps `nix develop -c` for cargo/verifier work: those need the
# full shell and are heavyweight anyway.
{ ... }:
{
  perSystem = { pkgs, config, toolchains, ... }:
    let
      treefmtBin = "${config.treefmt.build.wrapper}/bin/treefmt";
      hookConfig = {
        pre-commit = {
          parallel = true;
          commands = {
            treefmt = {
              glob = "*.{nix,rs,py}";
              run = "${treefmtBin} --fail-on-change --no-cache {staged_files}";
            };
            clj-kondo = {
              glob = "*.{clj,cljs,cljc,edn}";
              run = "${pkgs.clj-kondo}/bin/clj-kondo --lint {staged_files}";
            };
            regex-compile = {
              glob = "verifiers/*/rules/booklogic/lifts.edn";
              run = "${toolchains.pythonEnv}/bin/python scripts/regex-compile-check.py {staged_files}";
            };
            readme-lint = {
              glob = "README.md";
              run = "bash -c 'cd tools/readme-lint && .venv/bin/python -m scripts.lint_readme'";
            };
          };
        };
        pre-push = {
          parallel = false; # tasks contend for the cargo target dir
          commands = {
            scaffold-bake.run =
              "${toolchains.pythonEnv}/bin/python -m pytest skills/neurosym-forge/tests/test_scaffold_bake.py -x";
            regression-suite.run =
              "${toolchains.pythonEnv}/bin/python -m pytest skills/neurosym-forge/tests/regression/ -x";
            # No nextest hook: there is no top-level cargo workspace (see the
            # Makefile nextest comment); the old `cargo nextest run --workspace`
            # hook errored on every push from a hook-installed clone. Per-crate
            # rust tests run via smoke-changed's verifier `ci` targets.
            smoke-changed = {
              glob = "verifiers/**";
              run = "nix develop -c bash -c 'for d in $(git diff --name-only origin/main...HEAD verifiers/ | cut -d/ -f1-2 | sort -u); do make -C \"$d\" ci || exit 1; done'";
            };
          };
        };
      };
    in
    {
      packages.lefthook-config =
        (pkgs.formats.yaml { }).generate "lefthook.yml" hookConfig;
      # The top-level attr names ARE the git hook names; shells.nix derives
      # its hook-script installer from this so the set lives in one place.
      _module.args.lefthookHooks = builtins.attrNames hookConfig;
    };
}
