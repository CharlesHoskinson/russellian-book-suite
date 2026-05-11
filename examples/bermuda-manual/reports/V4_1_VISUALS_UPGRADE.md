# v4.1 Visuals Upgrade — Bermuda Manual

Run date: 2026-05-11

## Why

The v4 PDF had 12 figures but four of them — the parish map, government org chart, court hierarchy, education pipeline, healthcare flow, ferry routes — were hand-authored SVG that read as schematic and amateur (the parish map was a row of slanted parallelograms, the org charts were basic box-and-arrow with no curves).

## What changed

**Three new tools installed locally:**

- **Mermaid CLI** (`@mermaid-js/mermaid-cli`, MIT) — re-renders the four flow/hierarchy diagrams with editorial-grade typography, routing, and themes. Uses Playwright's bundled Chromium (no second browser download).
- **geopandas + shapely + pyproj** (BSD/MIT) — renders real polygon geometry from a 9-feature Bermuda parishes GeoJSON.
- **plottable** (MIT) — installed for hero-table rendering; not yet wired into the v4.1 build (kept for v4.2).

**One new public-domain data file:**

- `bermuda-parishes.geojson` — pulled from OpenStreetMap via Overpass API (`admin_level=6` + `border_type=parish`), simplified at ~16-metre Douglas–Peucker tolerance to 62 KB. Licensed ODbL, credited in the PDF source note. 9 features (8 MultiPolygon, 1 Polygon for Devonshire).

## Diagram-by-diagram

| Figure | Before | After |
|---|---|---|
| Parish map | Row of 9 coloured parallelograms; schematic only | Real OSM polygon boundaries via geopandas; labelled with `representative_point`; OSM credit line beneath |
| Ferry routes | Same parallelogram schematic with dashed lines | Faded parish polygons as basemap + Hamilton hub + four routes to real endpoint coordinates |
| Government org chart | Hand-SVG five-box layout | Mermaid flowchart with serif Georgia typography, role descriptions in italic, curved routing, classDef styling |
| Court hierarchy | Same | Mermaid flowchart with labelled edges ("appeal", "leave required"), apex styling for Privy Council |
| Education pipeline | Hand-SVG seven-box layout | Mermaid left-right flowchart, alternate-track styling for private/parochial, destination styling for overseas |
| Healthcare flow | Same | Mermaid flowchart with insurer/provider class distinction, labelled premium/claims/referral edges |

The matplotlib charts (climate, GDP pie, population line, cost comparison, rent bars, tourism arrivals) were re-themed against tvhahn's publication-quality matplotlib defaults: serif fonts, despined axes, dotted grids, value labels on bars, in-figure annotations for peaks and the pandemic dip.

## Skills surveyed (research artifact)

Three research agents surveyed:

1. **Anthropic-official skills.** Catalogue covers fine-art generation (canvas-design, algorithmic-art), document containers (pdf, docx, pptx, xlsx), HTML scaffolding (web-artifacts-builder, frontend-design), theming (theme-factory, brand-guidelines). Nothing for labeled diagrams or data charts.
2. **Community skills.** Strong candidates: `baoyu-diagram` (17.8k-star parent, Claude-authored SVG), `Agents365-ai/mermaid-skill`, `tvhahn/matplotlib-skill`, `davila7/claude-code-templates/scientific-visualization`, `davila7/.../geopandas`.
3. **Underlying libraries.** Best-in-class: D2 / Mermaid (diagrams), geopandas + contextily (maps), great_tables / plottable (tables), matplotlib (charts).

Final picks: **Mermaid CLI** for diagrams, **geopandas** for maps, **plottable** held for v4.2, **matplotlib-skill defaults** applied inline.

## Output

`C:\bermuda-manual\book\releases\3.0.0\`

| Artifact | Size |
|---|---:|
| manuscript.pdf | 1.29 MB |
| manuscript.html | 632 KB |
| manuscript.md | 147 KB |

PDF: **73 pages**, 12 figures rendered (Mermaid SVGs + geopandas PNGs + matplotlib PNGs), no inline citation tokens, no claim-catalogue back matter.

## Files of record

- New figure generator: `C:\tmp\generate_bermuda_figures_v2.py`
- Mermaid sources: `C:\tmp\mermaid\*.mmd`
- Puppeteer config (uses Playwright's bundled Chromium): `C:\tmp\puppeteer-config.json`
- Bermuda parishes GeoJSON: `C:\bermuda-manual\chapters\assets\shared\bermuda-parishes.geojson`
- Updated figure assets: `C:\bermuda-manual\chapters\assets\shared\` and `C:\bermuda-manual\book\assets\shared\`
- Finalization script: `C:\tmp\finalize_v4_1.py`

## Carry-over

- The hero-table upgrade with `plottable` (cost-comparison budget tables, climate normals) is held for v4.2.
- The full v4 skill stack (the `book-craft` skill) is still scoped in `~/.claude/skills/book-compose/docs/superpowers/plans/2026-05-10-book-craft-v4-and-bermuda-regen.md`. v4.1 applied design patterns directly; the skill itself can be built when there's appetite.
- `D2` was evaluated but skipped (Mermaid covers the same diagram families with a lighter footprint and is already integrated).
