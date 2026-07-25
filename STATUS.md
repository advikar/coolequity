# CoolEquity — build status & handoff

Resume point for a fresh session. Spec lives in `../CoolEquity_BUILD_PROMPT.md`.

## Run it

```bash
cd coolequity
python3 -m http.server 8000       # then open http://localhost:8000/app/
```

Pipeline (venv already built at `.venv`), run from `pipeline/`:

```bash
../.venv/bin/python 01_make_grid.py
../.venv/bin/python 02_satellite.py      # --cached to skip the network
../.venv/bin/python 03_census.py
../.venv/bin/python 04_overlays.py       # --refresh to re-pull OSM/HOLC
../.venv/bin/python 05_score.py
```

Note the two flags are opposites on purpose. 02 goes live by default and
`--cached` forces the cache; 04 uses the cache by default and `--refresh` forces
live, because Overpass rate-limits and re-pulling 645 amenities on every tweak
is how you get 504'd an hour before the demo.

## Where we are

| Phase | State | Output |
|---|---|---|
| 0 Front end decoupled | done | `app/index.html` fetches `data/la.geojson` |
| 1 H3 grid | done | `data/grid.geojson` — 3486 res-8 hexes, 0.82 km² each |
| 2 Satellite LST + NDVI | done | `data/satellite.csv`, `data/{lst,ndvi}.tif` |
| 3 ACS census | done | `data/census.csv`, `data/acs.csv` |
| 4 Overlays | done | `data/overlays.csv`, `centers.geojson`, `holc_la.geojson`, `places.geojson` |
| 5 Score + rank | done | `data/la.geojson` — 3008 scored hexes, **app now on real data** |
| 6 Polish + demo | done bar the video | `README.md`, `DEMO.md`, `app/vendor/` |

Verified in the browser at 1440×860: priority, redlining and cooling-access
layers all render and the legend matches the map; ROI panel produces sane
numbers on the #1 hex. Re-verified after the Phase 6 edits, on both the CARTO
and the flat basemap paths — `?flat=1` shows **zero** off-host requests.

**The only thing left on the whole build is the 60s screen capture**, which is a
manual step; instructions are at the bottom of `DEMO.md`.

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
8. **Overpass `out center tags`** — the `tags` verbosity prints ids and tags and
   **drops coordinates**, including on plain nodes. Every element parsed fine and
   then had nowhere to go, so the place-name query silently returned zero
   features. Use `out center`. `check_coords()` now hard-fails instead of
   silently dropping.
9. **Data layers added on `map.on('load')`** — bug 5 one level deeper, and the
   lesson had not been carried across. Measured: a tab opened in the background
   reports `document.hidden=true`, `map.loaded()=false` *forever*, and presents a
   blank map when you switch to it. `isStyleLoaded()` never settles either.
   Sources and layers are now **baked into the style object before the map is
   constructed**, so no event is involved at all.
10. **`fitBounds` padding larger than the container** → throws
    `Invalid LngLat object: (Infinity, NaN)`. Thrown inside `boot()`'s promise
    chain it took down the whole map and reported it as "could not load
    la.geojson", sending you to debug the wrong layer. `fitData()` clamps padding
    and defers on a zero-sized container; the catch handler now distinguishes
    "data failed" from "map failed".
11. **MapLibre loaded from unpkg** — the risk register's whole answer to "venue
    Wi-Fi dies" is *"app + all data are static/local"*, and a `<script src=unpkg>`
    quietly made that false. With no network `maplibregl` is undefined and the map
    never gets as far as the basemap fallback that was built for exactly this.
    Now vendored at `app/vendor/` (v4.7.1, BSD-3; its CSS inlines every icon as a
    `data:` URI, so nothing else leaks out). **Audit the whole page for off-host
    requests, not just the ones you wrote a fallback for.**
12. **`setLayer` gated on `map.getLayer('fill')`** — `getLayer()` returns
    undefined until the style parses, so a layer toggled during the basemap fetch
    updated the legend, chip and caption while the map kept the old ramp. **The
    legend silently lying about the map is the worst failure mode here.**
    `paintFill()` retries on `styledata`.

## Open issues / decisions taken

- **`corr(LST, green)` — RESOLVED, and it is negative.** The +0.091 across all
  3486 hexes was entirely the 478 uninhabited ones (ocean reads 18.4 °C with zero
  vegetation). Across the 3008 populated hexes **r = −0.606**, and it holds
  inside every longitude band (−0.35 to −0.69), so it is not LA's coastal
  gradient. Partial correlation after removing a quadratic lon/lat trend is
  **−0.577**. The "shade cools" narrative is safe to say out loud.
- **478 uninhabited hexes — DROPPED** (`config.MIN_POP`). Justified above: they
  invert the headline correlation and stretch the heat ramp over a range no
  inhabited hex occupies. The map now has honest holes over the bay, Griffith
  Park and the Sepulveda Basin.
- **`pct65` degenerate shares — FIXED** by empirical-Bayes shrinkage toward the
  citywide rate with a 100-person pseudo-count (`config.AGE65_SHRINK_POP`). Raw
  max was 100% (a 4-person hex); smoothed max is 47.4%, median 15.2%. A
  5,000-person hex keeps 98% of its own weight. Without it the Age-65 ramp was
  set by a 4-person artefact and went flat.
- **Hex names — DONE, from OSM place nodes**, not a US neighborhood file, so the
  same code names hexes in Lagos or Delhi. 308 place nodes → nearest-node join,
  with a compass suffix to keep the ranked list unique ("Westlake S",
  "Koreatown SE"). 1450 of 3008 need a numeric suffix too, but those are
  low-density mountain hexes that rank last; the dense core reads well.
- **Walk time is a circuity-adjusted straight line, not a route.** `CIRCUITY =
  1.273` = 4/π, the exact expected Manhattan-to-Euclidean ratio over uniform
  bearings — the penalty for a perfect street grid, which is close to what LA is.
  A real osmnx walk graph over this 3,400 km² bbox is millions of nodes and tens
  of minutes of Overpass download; that does not belong on a demo's critical
  path. **Say "estimated walking minutes", never imply it is routed.**
- Population totals 6.48M vs the county's 9.85M — expected, the bbox covers the
  LA basin, not Antelope Valley. Visible as a hard straight edge on the east side
  of the hex layer around El Monte / Whittier. Not a bug; know it before a judge
  points at it.

## Phase 6 — what was done

1. **The two false claims in spec Section 10 are corrected**, in the spec itself
   (with a "superseded, rehearse from DEMO.md" banner) and in the new `DEMO.md`,
   which is now the rehearsal doc. The real table:

   | HOLC | hexes | mean LST | mean green | mean walk | mean score |
   |---|---|---|---|---|---|
   | A | 136 | 38.7 °C | 26.0% | 20.3 min | 24.4 |
   | B | 200 | 42.7 °C | 18.5% | 14.3 min | 38.4 |
   | C | 450 | 45.1 °C | 12.2% | 13.2 min | 52.0 |
   | D | 260 | 45.4 °C |  9.4% | 12.2 min | 54.1 |

   A→D gap is **+6.7 °C**, not ~10. And D areas are **closer** to relief
   (12.2 vs 20.3 min), not twice as far — dense inner-city blocks have libraries;
   A-graded areas are leafy low-density suburbs. Reframed in `DEMO.md` as
   "redlining shows up here as heat and missing canopy, not as distance."
2. **Real ROI numbers are in the closing beat** (hex #1, Westlake S): canopy
   3% → 15%, −0.36 °C, 15,759 residents, 1,797 aged 65+, ~2,470 trees over
   0.82 km², ≈ $1.2M, $78/resident. Re-verified against the live app, not just
   recomputed from the geojson.
3. **The repo now genuinely runs with no network** — see fixed bug 11. Confirmed
   by counting off-host requests in the page: 0 on `?flat=1`, and on the normal
   path the only ones are CARTO's own basemap assets. `data/_cache/` stays
   gitignored; it is pipeline scratch, nothing the app reads.
4. **`README.md` written** — run instructions, pipeline order, score and ROI
   formulas, provenance, and an explicit "what's estimated" section.

### Still open

- **Record the 60s screen capture.** Manual; steps at the bottom of `DEMO.md`.
  It covers the failure vendoring doesn't: this laptop dying and someone else
  having to present.
- Stretch goals in spec Section 11 (city selector, budget optimizer, CSV export)
  are untouched and remain optional.

## Contract between pipeline and front end

Hex properties the app reads. Renaming any of these breaks the UI:

```
id  name  lst  green  pop  pct65  ac  holc  access_min  access_km  score  rank  area_m2
```

`holc` is legitimately `null` outside the 1939 map (1962 of 3008 hexes) — the
fill expression's `match` default handles it. Score weights live in
`pipeline/config.py` **and** are described in the app's legend copy — keep in sync.

## Notes

- `.env` holds `CENSUS_API_KEY`, gitignored, mode 600, never committed.
- Satellite path is Planetary Computer (anonymous). No Earth Engine account needed.
- Overpass mirrors are tried in order with backoff; `overpass.kumi.systems` leads
  because the main instance throttles hardest.
- `?data=<name>` on the app URL swaps the hex file (e.g. `?data=grid`).
- `?flat=1` forces the flat basemap, so the no-network look is rehearsable
  without actually killing the Wi-Fi. The county outline is drawn only on that
  path — over CARTO's streets it is clutter, over nothing it is the only thing
  telling you the holes over the bay are holes.
- The app needs ~700px of width before the map column is usable; below that the
  366px panel eats the grid. Fine for a projector, worth knowing on a laptop.
