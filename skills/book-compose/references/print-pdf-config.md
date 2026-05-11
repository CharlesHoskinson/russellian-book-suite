# Print PDF Configuration

`scripts/print_pdf.py` renders `manuscript.html` to `manuscript.pdf` using headless Chromium via Playwright. The PDF is a print artifact of the HTML, not an independent typesetting pass. Every typographic decision lives in the HTML's CSS; this script only drives the headless browser.

## Playwright launch options

`print_pdf` opens a single Chromium instance per call. The launch options:

- `headless=True`. The browser runs without a window. The script never expects a display server and works on CI runners.
- Chromium engine. Firefox and WebKit are not used. Chromium's print pipeline is the most predictable for `@media print` and Tailwind `print:` variants.

The browser is closed in a `finally` block whether the print succeeds or fails. The script never leaves a Chromium process behind.

## Chromium installation

Playwright separates the Python package from the browser binaries. Installing the package alone is not enough. The build-book pipeline checks both via `is_playwright_ready()`.

Install Chromium with:

```
.venv\Scripts\python.exe -m playwright install chromium
```

The download is roughly 300 MB and lands inside Playwright's own browsers cache (under `%USERPROFILE%\AppData\Local\ms-playwright\` on Windows). One install per machine suffices; subsequent builds reuse the cache.

If the install step is skipped, `is_playwright_ready()` returns False, `build_book` skips the PDF render silently, and `outputs` in `book-manifest.yaml` omits `manuscript.pdf`. The HTML and Markdown artifacts still land in the bundle.

## Page format and margins

The `page.pdf()` call sets:

- `format="A4"`. International standard. 210mm x 297mm. Use this for distribution outside North America and for academic publishing pipelines.
- `margin={"top": "25mm", "right": "20mm", "bottom": "25mm", "left": "20mm"}`. Top and bottom are wider than the sides to give the running header and footer room without crowding body text.
- `print_background=True`. Backgrounds and shaded blocks render as the CSS specifies them. Code blocks keep their tinted background; callout boxes keep their accent fill.

A4 is hard-coded. Operators who need US Letter must edit `print_pdf.py` directly; a config knob is intentionally absent to keep the bundle reproducible across machines.

## Header and footer template

The script enables `display_header_footer=True` and supplies inline HTML for both bands.

The header is intentionally empty: `header_template="<div></div>"`. Putting the book title in the header competes with the chapter title for the reader's eye and adds noise to a PDF that already has a generated TOC.

The footer carries the page number:

```html
<div style="font-size:9px;width:100%;text-align:center;color:#666;">
  <span class="pageNumber"></span> / <span class="totalPages"></span>
</div>
```

Chromium injects the live values into `pageNumber` and `totalPages` at print time. Inline styles are required because Chromium loads header and footer templates without the page's stylesheet. The 9-pixel size and grey color match the conventional academic footer weight.

## Print-media emulation

The script calls `page.emulate_media(media="print")` before `page.pdf()`. The emulation switches the rendered DOM into the `@media print` branch of every stylesheet. Tailwind's `print:hidden`, `print:block`, and `page-break-before` rules become active. Without emulation Chromium would print the screen view and the TOC sidebar, search bar, and theme toggle would all bleed into the PDF.

The emulation is local to the page; the live HTML on disk is unchanged.

## `wait_until="networkidle"`

`page.goto(file_url, wait_until="networkidle")` blocks until the network is quiet for 500ms. Two reasons:

1. The React app inside `manuscript.html` may fetch fonts, syntax-highlighting stylesheets, or Mermaid scripts at boot. Printing before those finish loading produces a half-rendered PDF.
2. The book payload deserialization happens at React mount. `networkidle` is a coarse but reliable proxy for "the React app has finished its first render."

`load` and `domcontentloaded` fire too early; `networkidle` errs on the side of correctness at the cost of a small wait.

## How `is_playwright_ready()` gates `print_pdf`

`build_book` never calls `print_pdf` blindly. It calls `is_playwright_ready()` first. The check:

1. Tries `from playwright.sync_api import sync_playwright`. A missing package returns False.
2. Resolves `chromium.executable_path` and confirms the binary exists on disk.

Both must succeed before `print_pdf` runs. If the check returns False, `build_book` logs nothing scary, skips the render, and continues. If the check returns True but the print itself raises, `build_book` catches the exception, prints `warning: PDF render failed: ...`, and continues without `manuscript.pdf` in the outputs list. The book release never fails because of a missing PDF.

## Smoke test

Use this to verify the PDF pipeline against a built bundle:

```
.venv\Scripts\python.exe -c "from scripts.print_pdf import print_pdf; from pathlib import Path; print_pdf(Path('book/releases/v0.1/manuscript.html'), Path('book/releases/v0.1/manuscript.pdf'))"
```

Expected outcome: `manuscript.pdf` appears in the release directory, opens in any PDF viewer, shows the chapter `h1` blocks each on their own page, shows page numbers in the footer, and does not contain the TOC sidebar, search bar, or theme toggle.

If the file is missing or empty, run `is_playwright_ready()` directly to confirm Chromium is installed:

```
.venv\Scripts\python.exe -c "from scripts._playwright_check import is_playwright_ready; print(is_playwright_ready())"
```

Expected: `True`. False means the Chromium install step has not run.
