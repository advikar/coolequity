# CoolEquity — build status & handoff

Resume point for a fresh session. Spec lives in `../CoolEquity_BUILD_PROMPT.md`.

## Run it

```bash
cd coolequity
python3 -m http.server 8000       # then open http://localhost:8000/app/
```

Pipeline (venv already built at `.venv`):

```bash
cd pipeline
../.venv/bin/python 01_make_grid.py
../.venv/bin/python 02_satellite.py      # --cached to skip the network
../.venv/bin/python 03_census.py
```

## Where we are

| Phase | State | Output |
|---|---|---|
| 0 Front end decoupled | done | `app/index.html` fetches `data/la.geojson` |
| 1 H3 grid | done | `data/grid.geojson` — 3486 res-8 hexes, 0.82 km² each |
| 2 Satellite LST + NDVI | done | `data/satellite.csv`, `data/{lst,ndvi}.tif` |
| 3 ACS census | done | `data/census.csv`, `data/acs.csv` |
| 4 Overlays | **next** | HOLC, cooling centers, walk time, **hex names** |
| 5 Score + rank | todo | writes `data/la.geojson` (app still on mock data until this runs) |
| 6 Polish + demo | todo | |

## Bugs already fixed — do not reintroduce

1. **`LAYERS['holc']` missing** → `setLayer('holc')` threw, redlining toggle dead.
2. **`#detail` had no `position`** → flowed as a third grid cell, halved the map.
3. **`AREA_M2` hardcoded to 5.16 km²** (a res-7 value). Real hexes are 0.82 km²;
   ROI overstated trees and cost by 6.3×. Now reads per-hex `area_m2`.
4. **UI init gated on `map.on('load')`** → blank screen on a slow CDN. Panel now
   renders from data first.
5. **Basemap fallback keyed on `map.on('load')`** — `load` waits on the first
   render, so a backgrounded tab (rAF suspended) is indistinguishable from a dead
   CDN, and the fallback tore down a working map. Now probes the style URL directly.
   **Never key a fallback on `load`.**
6. **Sentinel-2 BOA offset** — baseline ≥04.00 carries `BOA_ADD_OFFSET = -1000`
   that Planetary Computer does not pre-apply. It does *not* cancel in a ratio.
   Without it NDVI maxed at 0.50 instead of 0.79.
7. **NDVI clamp** — spec's 0.20–0.80 floored 40.5% of hexes at 0% green.
   Now 0.05–0.65 (physical endpoints, must stay absolute — canopy % feeds ROI).

## Open issues for Phase 4/5

- **`corr(LST, green) = +0.091`, expected negative.** Suspected confound: ocean
  hexes (LST min 18.4 °C is sea surface) plus LA's coastal/inland climate
  gradient — the coast is cool *and* unvegetated, the valley hot *and* irrigated.
  Re-test on populated land hexes only before trusting it. If real, it does not
  break the score (heat and greenness enter as separate weighted terms) but it
  does undercut the "shade cools" narrative, so know the answer before demoing.
- **478 uninhabited hexes** (ocean, mountains). Decide in Phase 5 whether to drop
  them — they stretch the LST min and clutter the map. Leaning: drop `pop < 1`.
- **`pct65` max is 100%** — tiny-population hexes produce degenerate shares.
  Consider flooring the share at some minimum population.
- **Hex names.** H3 cells have none; the demo script and ranked list need them.
  Not budgeted in the spec. Plan: join LA Times Mapping LA neighborhood polygons.
- Population totals 6.48M vs the county's 9.85M — expected, the bbox covers the
  LA basin, not Antelope Valley. Not a bug.

## Contract between pipeline and front end

Hex properties the app reads. Renaming any of these breaks the UI:

```
id  name  lst  green  pop  pct65  ac  holc  access_min  access_km  score  rank  area_m2
```

Score weights live in `pipeline/config.py` **and** are described in the app's
legend copy — keep them in sync.

## Notes

- `.env` holds `CENSUS_API_KEY`, gitignored, mode 600, never committed.
- Satellite path is Planetary Computer (anonymous). No Earth Engine account needed.
- `app/index.html` footer still says "mock data for UI review" — must change in Phase 6.
- `?data=<name>` on the app URL swaps the hex file (e.g. `?data=grid`).
