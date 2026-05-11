# Pandoc Templates

The skill ships three Pandoc assets under `assets/pandoc/`. They are defaults; per-book overrides take precedence. The Pandoc binary is a local subprocess; no remote rendering occurs.

## Shipped templates

### `assets/pandoc/manuscript.tex`

LaTeX template used for the `pdf` and `latex` output formats. Document class is `book` at 11pt on A4 paper. Imports `microtype`, `hyperref`, `listings`, `xcolor`. The `listings` package is configured for monospaced source listings with single-frame borders and break-on-overflow lines. Pandoc variables consumed by the template: `$title$`, `$author$`, `$date$`, `$body$`. The template emits a title page and a table of contents before the body.

The template is intentionally minimal. Books that need a custom title page, custom chapter-opening typography, or sidenotes override the template per-book (see "Per-book overrides" below).

### `assets/pandoc/manuscript.html5`

HTML5 template used when the user adds an `html` output target. The skill does not currently ship `html` in the supported `output_formats`, but the template is present for forward compatibility.

### `assets/pandoc/citation-style.csl`

Citation Style Language stylesheet. The shipped file is a minimal placeholder that emits citation-numbers in the body and renders bibliography entries as their title text. It is not suitable for production: replace it with `chicago-author-date.csl` from the citation-style-language repository at `https://github.com/citation-style-language/styles` before building a publishable bundle.

The placeholder exists so that the build does not crash on a missing CSL when Pandoc's `--csl` flag is supplied. In the default build invocation, `--csl` is not supplied; Pandoc falls back to its built-in numeric style.

## Per-book overrides

A workspace's `CLAUDE.md` may override the shipped assets. The override mechanism reads three optional keys from the workspace metadata block:

```yaml
book-compose:
  pandoc_template: assets/my-template.tex
  pandoc_csl:      assets/my-style.csl
  pandoc_engine:   lualatex
```

Paths are resolved relative to the workspace root. When a key is set, `build_release_bundle.py` uses the override; when a key is unset, the shipped default is used. The override mechanism is silent: a missing per-book file falls back to the default without warning, on the assumption that the workspace is mid-construction. Operators who require strict template selection should verify the rendered PDF's first page after each build.

## XeLaTeX versus LuaLaTeX

The shipped build uses `--pdf-engine=xelatex`. XeLaTeX handles UTF-8 source natively, supports system fonts via `fontspec`, and produces correct output for the Latin, Greek, and most Cyrillic scripts found in technical writing. It is the right default.

LuaLaTeX is required when the document depends on:

- Complex font shaping (CJK ideographs, Indic conjuncts, Arabic shaping in flowed paragraphs).
- LuaTeX-specific packages (`luaotfload`, `luacolor`, `luatextra`).
- In-document Lua scripting via `\directlua`.
- OpenType features beyond what `fontspec` exposes by default (e.g. arbitrary feature-set toggles per glyph run).

Override the engine via the workspace's `CLAUDE.md`:

```yaml
book-compose:
  pandoc_engine: lualatex
```

LuaLaTeX is slower than XeLaTeX, sometimes by a factor of two or three on large documents. Do not switch engines without a concrete reason from the list above.

## Replacing the shipped CSL

Production builds replace `assets/pandoc/citation-style.csl` (or the per-book override path) with a real CSL file. The recommended baseline is `chicago-author-date.csl` from the citation-style-language repository. Other recognised baselines:

- `ieee.csl` for engineering venues.
- `nature.csl` for natural-science venues.
- `acm-sig-proceedings.csl` for ACM conferences.

To install the production CSL alongside the workspace, place it at `<workspace>/assets/citation-style.csl` and set the workspace's `CLAUDE.md` override:

```yaml
book-compose:
  pandoc_csl: assets/citation-style.csl
```

The build then passes `--csl <workspace>/assets/citation-style.csl` to Pandoc and emits citations in the chosen style.

## Graceful degradation when Pandoc is absent

The `_run_pandoc` helper in `scripts/build_release_bundle.py` is the single integration point with the Pandoc binary. It builds the argument vector, calls `subprocess.run(..., check=True, capture_output=True, text=True)`, and returns a boolean. The helper catches `FileNotFoundError` (the binary is not on `PATH`) and `subprocess.CalledProcessError` (the build invocation failed). Either outcome returns `False`; the calling code omits the corresponding output from the bundle and from the manifest's `outputs` list.

Markdown output is always produced because it is a file copy, not a Pandoc invocation. The user who has no Pandoc installed still receives `draft.md`, `evidence-summary.md`, `style-pass-report.md`, `claims-slice.jsonl`, and `manifest.yaml`. The bundle is still releasable as a Markdown distribution; the operator can render PDF later on a machine with Pandoc installed by re-running `_run_pandoc(bundle / "draft.md", bundle / "draft.pdf", "pdf")`.

The skill does not log Pandoc invocations to stdout. The captured stdout and stderr are discarded on success. On failure, they are also discarded, in keeping with the "build does not crash on missing Pandoc" contract. Operators who need to debug a Pandoc failure should re-run the same Pandoc invocation manually outside the helper.
