# LibreCharts branding

The logo is a chart: three ascending columns under a difference arrow — the annotation the
extension is known for. It uses the series palette of the default colour scheme
(`core/style.py`), so a deck and the logo share the same colours.

## Files

| File | Use |
|---|---|
| `logo-mark.svg` | The mark on its own (app icon, avatar, social preview). 512 × 512. |
| `logo-mark-small.svg` | Simplified mark for 32 px and below: no arrow, the tallest column in the accent colour. |
| `logo.svg` | Horizontal lockup: mark plus wordmark, for light backgrounds. 1120 × 400. |
| `logo-mark-{512,256,128,64,48}.png` | Raster marks, transparent background. |
| `logo-mark-{32,24,16}.png` | Raster marks from the small variant. |
| `logo-{1120x400,560x200}.png` | Raster lockups, transparent background. |

The SVGs are the source; the PNGs are rendered from them. Keep the two in step when the
artwork changes.

## Colours

| Role | Colour |
|---|---|
| Tile (top → bottom) | `#1E3F68` → `#12253F` |
| Column 1 | `#C9D8EE` |
| Column 2 | `#8FB4E3` |
| Column 3 | `#5E8AC7` |
| Arrow, accent column | `#F4B183` |
| Wordmark "Libre" | `#1E3F68` |
| Wordmark "Charts" | `#5E8AC7` |

## Rules

- Keep clear space of at least a quarter of the mark's width around the lockup.
- Do not recolour the columns, rotate the mark, or add effects.
- On a dark background use the mark alone; the wordmark's dark blue does not carry.
- The wordmark is set in Segoe UI Bold (fallback: Liberation Sans, DejaVu Sans) and is not
  outlined yet: render from the SVG where a font is available, or use the PNGs.
