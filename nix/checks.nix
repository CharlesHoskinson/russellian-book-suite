# Pure gates as flake checks. Sandbox rule (design.md §1): pure -> checks.*,
# impure (network, cargo builds, npm ci) -> Makefile verb under `nix develop`.
{ self, ... }:
{
  perSystem = { pkgs, toolchains, ... }:
    let
      # Writable copy for tools that drop caches/artifacts next to sources.
      withSrcCopy = name: env: script: pkgs.runCommand name env ''
        cp -r ${self} src && chmod -R u+w src && cd src
        ${script}
        touch $out
      '';
    in
    {
      checks = {
        clj-kondo = pkgs.runCommand "clj-kondo-lint"
          { buildInputs = [ pkgs.clj-kondo pkgs.findutils ]; } ''
          cd ${self}
          files=$(find . -type f \( -name '*.clj' -o -name '*.cljs' \
            -o -name '*.cljc' -o -name '*.edn' \) -not -path './.clj-kondo/*')
          clj-kondo --cache-dir "$TMPDIR/kondo-cache" --lint $files --fail-level error
          touch $out
        '';

        invariant-lint = withSrcCopy "invariant-lint"
          { buildInputs = toolchains.python; } ''
          python -m ci.lint_no_direct_http
          python -m ci.check_windows_canary
          python -m pytest ci/ -q -p no:cacheprovider
        '';

        neurosym-drift = withSrcCopy "neurosym-drift"
          { buildInputs = toolchains.python; } ''
          python -m pytest skills/neurosym-forge/tests/test_support_matrix.py -q -p no:cacheprovider
          python -m pytest skills/neurosym-forge/tests/test_induction_grammar_drift.py -q -p no:cacheprovider
        '';

        required-name = pkgs.runCommand "required-name"
          { buildInputs = [ pkgs.bash pkgs.gawk pkgs.gnugrep pkgs.gnused ]; } ''
          bash ${self}/scripts/check-required-name.sh
          touch $out
        '';
      };
    };
}
