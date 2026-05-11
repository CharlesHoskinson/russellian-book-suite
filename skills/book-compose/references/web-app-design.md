# Web App Design

The book release ships with an interactive HTML browser. The design separates the deterministic skeleton from the LLM-rendered React app. The skeleton is reproducible byte-for-byte. The React app is rendered once per build and stored in the same file.

## Two-stage rendering

Stage one is deterministic. `scripts/render_book_html.py:write_html_skeleton` reads `assets/book-html-skeleton.html`, substitutes the book title, inlines the book payload as JSON, and writes `manuscript.html`. The output is identical for identical inputs. No LLM call. No network call.

Stage two is LLM-driven. Claude invokes the `web-artifacts-builder-anthropic` Skill tool. The skill reads the inlined payload, generates a React+Tailwind+shadcn book browser, and writes the rendered components into the skeleton in place of the `BOOK_APP_INSERTION_POINT` marker. The skill writes back to the same `manuscript.html` file. Everything before and after the marker stays byte-for-byte identical.

The split exists for two reasons. First, a deterministic skeleton means the build is reproducible without depending on the React app rendering being deterministic. Second, the payload survives the React render, so a downstream tool can re-render the app from the same data without re-running the build.

## The BOOK_APP_INSERTION_POINT marker

The string `<!-- BOOK_APP_INSERTION_POINT -->` appears once inside `<div id="book-app-root">` in the skeleton. It is the only place the React app is allowed to write. The marker is a literal HTML comment so a static viewer renders the surrounding fallback content without errors. The web-artifacts-builder-anthropic skill replaces the marker with the React app's mount point and inline component definitions.

The fallback content immediately after the marker is a `<div class="skeleton-notice">` plus a static `<h1>` and one paragraph. A reader who opens `manuscript.html` before the React render still sees a usable page that points at the embedded payload.

## The two embedded `<script>` blocks

Two script tags carry the data. They live at the bottom of `<body>`, outside `#book-app-root`, so the React app can read them by id at startup.

`<script id="book-payload" type="application/json">` holds the JSON returned by `build_book_summary`: `book_id`, `book_title`, `total_words`, `total_claims`, `chapters` array, and `sources_bibliography`. The React app parses this with `JSON.parse(document.getElementById('book-payload').textContent)`.

`<script id="book-manuscript" type="text/markdown">` holds the concatenated `manuscript.md` text. The type is non-executable so the browser does not run it. The React app reads `.textContent` and renders it through a Markdown renderer.

`render_book_html._escape_for_script_block` rewrites `</script` to `<\/script` in the manuscript text before injection. Without that escape a Markdown body containing the literal string `</script>` would break the embedded block.

## Required components

The React app must render seven components. The web-artifacts-builder-anthropic invocation passes this list as a hard requirement.

- TOC sidebar. Lists every chapter from `payload.chapters` with click-to-jump anchors into the reader pane. Sticky on the left at desktop widths, collapsible on mobile.
- Reader pane. Renders the manuscript Markdown. Supports headings, lists, fenced code, footnotes, and Mermaid blocks. Anchors match the TOC entries.
- Executive summary card. Displays `book_title`, `total_words`, `total_claims`, and a short top-of-book abstract. Stays visible on the home view.
- Per-chapter abstract cards. One card per chapter. Shows chapter title, purpose, abstract seed, word count, and claim count. Clicking a card opens the chapter in the reader pane.
- Source bibliography. Renders `sources_bibliography` as a list. Each entry is a `doc_id` from the workspace.
- Search bar. Free-text search across chapter titles, headings, and manuscript body. Results jump to the matching anchor.
- Theme toggle. Light and dark modes via Tailwind's `dark:` variants. Preference persists in `localStorage`.

## Print CSS rules

The HTML render must produce a clean PDF when Chromium prints it. Tailwind's `print:` variants control this. Treat the rules below as load-bearing.

- `print:hidden` on the TOC sidebar, search bar, theme toggle, and any download buttons. The print version is paginated text; navigation chrome is noise on paper.
- `page-break-before: always` on every `h1` so each chapter starts on a new page.
- `page-break-before: avoid` on the first `h1` of the document so the cover page is not preceded by a blank page.
- `page-break-inside: avoid` on figure blocks and code fences shorter than one page so they do not split awkwardly.

The skeleton already ships with a minimal `@media print` block that hides the listed selectors and applies the page-break rules at the HTML level. The React app should reproduce these rules using Tailwind's `print:` variants on the equivalent elements; that keeps the rules attached to the components they govern.

## Replacing the skeleton with the React app

Stage 6 of the workflow performs the replacement. The steps:

1. Stage 6 step 3 has already produced `manuscript.html` with the skeleton, the marker, and the inlined payload.
2. Claude invokes the `web-artifacts-builder-anthropic` Skill tool.
3. The skill reads `summary.json` and the manuscript text. It generates the React+Tailwind+shadcn components.
4. The skill writes the components into `manuscript.html` at the `BOOK_APP_INSERTION_POINT` marker. The script blocks at the bottom remain untouched.
5. `build_book` then runs `print_pdf` against the now-rendered `manuscript.html` if Playwright is available.

The React render is the only step that is not pure Python. It is also the only step that is not deterministic. Pinning the web-artifacts-builder-anthropic skill version is therefore the contract that bounds reproducibility for `manuscript.html`.
