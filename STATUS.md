# CoolEquity — build status & handoff

Resume point for a fresh session. Spec lives in `SPEC.md` (in-repo since Phase 6;
Section 10 of it is superseded by `DEMO.md`).

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
| 7 Front-end rebuild | done | landing screen, live weights, ramp inversion, units |

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
    `paintFill()` retries on `styledata`. **Generalised in Phase 7 to
    `styleOp()`** — the centre filter and the selection ring were both still
    behind `if(map.getLayer(id))`, i.e. the same bug in two more places. Route
    every style mutation through `styleOp`, and never through `getLayer`.
13. **`rgbOf()` digit-scraped its argument** — it only ever worked on `ramp()`'s
    `rgb(r,g,b)` output. Fed a raw `#rrggbb` from the ramp arrays it failed
    *plausibly*: `#b30000` → `rgb(NaN)`, `#5c3a17` → `[5,3,17]` → a grey that
    looked like a design choice, so every weight swatch and slider thumb was
    silently grey. Branch on the leading `#`. **A colour helper that accepts two
    notations has to test both.**
14. **Mercator y in radians against longitude in degrees** (intro backdrop) —
    the raw log-tangent is 57.3× too small, so LA drew as a 60 px horizontal
    smear rather than a city. Multiply by `180/π`. Any hand-rolled projection
    needs both axes in the same units.

## Phase 7 — the front-end rebuild

Driven by "it doesn't feel hackathon-winning": the map worked but the model was
invisible, the colours argued the opposite of the thesis, and there was no way
in other than being dropped on a map.

- **Ramps inverted, basemap lit.** One rule, stated in the legend under the bar
  with an arrow at the correct end: *deeper = more need*. The two protective
  inputs (canopy, A/C) ramp deep→pale so the arrow flips rather than the meaning.
  This forced CARTO **positron** — over dark-matter the deep end is the least
  visible ink on screen. The two changes only work together. `?flat=1`'s flat
  background is now light to match.
- **The four weights are live sliders.** Not a rebuild of the model — the same
  model. Verified in-page against the committed `la.geojson` at the shipped
  weights: **max 0.156 points, mean 0.039, pipeline ranks #1–#6 exact.** The
  residual is the geojson storing lst/green/ac at 1 dp. The pipeline's `score`
  and `rank` properties are never overwritten, so Reset is exact.
- The map repaints from a **MapLibre expression** that recomputes the score over
  the raw properties. Not `setData` — that re-serialises 1.4 MB per frame of a
  drag.
- **The legend caption for Priority is generated from the weights in force**, so
  the "keep config.py and the legend copy in sync" hazard below is retired for
  that layer. It is now impossible for the caption to quote 35% while the slider
  says 60%.
- Detail panel shows the **score arithmetic term by term** — measured value,
  position on the city's 0–1 scale, × weight, = points, then the population
  multiplier.
- **Cooling sites are classified** by the `kind` already in `centers.geojson`
  (library 212, community centre 200, pool 133, senior/shelter 100), each with a
  colour, a count read *from the file*, a plain-English definition and its own
  filter. Clicking one names it.
- **Landing screen** with a city picker. Only LA is built and the UI says so —
  the other cities are labelled *pipeline-ready* and show the actual build steps.
  A dropdown that appeared to load Delhi would be the worst thing in this repo.
  Backdrop is the real hex layer drawn to a canvas from the same geometry.
  `?go=1` (and any `?data=`) skips straight to the map.
- **Metric/imperial switch**, display-layer only. `fTemp` and `fTempD` are
  separate on purpose: a *drop* of 0.36 °C is 0.65 °F, not 32.65 °F.
- **Inter + Instrument Serif vendored** at `app/vendor/*.woff2` (latin subsets,
  63 KB, both OFL 1.1). Not a Google Fonts `<link>` — see fixed bug 11.

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

### Phase 7 browser verification — all clear

Everything in Phase 7 has now been checked in a real browser: console clean,
layer toggles confirmed to repaint the map via `queryRenderedFeatures` and not
just the legend, live model checked against `la.geojson`, units checked
including the temperature *delta*. The two items that had landed after the
previous browser pass were closed on the pass after that:

1. **The intro canvas backdrop is a city, not a band.** The `180/π` fix for
   fixed bug 14 renders correctly. Measured off the canvas pixels rather than
   eyeballed, because the smear it replaced was only ~60px tall and a thumbnail
   would not have settled it: ink spans 99.9% of canvas height and 85% of its
   width, and the left edge of the ink marches from x=0.16 at the top to x=0.69
   at the bottom — that diagonal is the LA coastline running NW→SE. A regression
   would flatten `vertFrac` toward zero. Re-measure with:

   ```js
   (()=>{const c=document.getElementById('intro-canvas'),g=c.getContext('2d');
     const d=g.getImageData(0,0,c.width,c.height).data;
     let minY=1e9,maxY=-1;
     for(let y=0;y<c.height;y+=2)for(let x=0;x<c.width;x+=2)
       if(d[(y*c.width+x)*4+3]>8){if(y<minY)minY=y;if(y>maxY)maxY=y;}
     return {vertFrac:+((maxY-minY)/c.height).toFixed(3)};})()   // expect ~0.999
   ```

2. **`?flat=1` makes zero off-host requests** — confirmed in the Network tab, not
   just statically audited. Every request is `localhost:8000`, a `data:` URI, or
   the MapLibre worker `blob:`. The flat path also *draws*: hexes plus the county
   outline, no basemap. That property is the whole answer to "what if the venue
   Wi-Fi dies", so re-check it in the Network tab after any change that touches
   `basemapStyle()` or adds an asset.

**A blank map screenshot during this pass was fixed bug 9 again, not a
regression.** The Browser pane backgrounds its tabs, `document.hidden` goes
true, rAF is suspended and the WebGL framebuffer is never repainted before
capture — while `queryRenderedFeatures({layers:['fill']})` returned 3,084. Trust
that query over a screenshot; front the tab (click into it) before believing a
blank frame.

Revert path if any of Phase 7 is unwanted: `git checkout pre-redesign -- app/`
(tag `pre-redesign` is the last pre-rebuild commit).

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
fill expression's `match` default handles it.

Score weights live in `pipeline/config.py` and are mirrored in the app's
`DEFAULT_W` / `DEFAULT_POPW`. **Those two must stay in sync** — that is the whole
basis of the "reproduces the pipeline" claim, and the check is one line in the
console:

```js
HEX.features.reduce((m,f)=>Math.max(m,Math.abs(sc(f.properties)-f.properties.score)),0)
// expect < 0.2 with the sliders at their defaults
```

The legend *copy* no longer needs syncing: it is generated from the weights in
force.

## Notes

- `.env` holds `CENSUS_API_KEY`, gitignored, mode 600, never committed.
- Satellite path is Planetary Computer (anonymous). No Earth Engine account needed.
- Overpass mirrors are tried in order with backoff; `overpass.kumi.systems` leads
  because the main instance throttles hardest.
- `?data=<name>` on the app URL swaps the hex file (e.g. `?data=grid`). Implies
  `?go=1`.
- `?go=1` opens straight onto the map, skipping the landing screen. Use it for
  rehearsal and for the recorded walkthrough.
- `?flat=1` forces the flat basemap, so the no-network look is rehearsable
  without actually killing the Wi-Fi. The county outline is drawn only on that
  path — over CARTO's streets it is clutter, over nothing it is the only thing
  telling you the holes over the bay are holes.
- The app needs ~700px of width before the map column is usable; below that the
  366px panel eats the grid. Fine for a projector, worth knowing on a laptop.
- Nothing off-host except CARTO's basemap: MapLibre, both typefaces and all data
  are local. Re-audit with `?flat=1` after any front-end change — that path must
  stay at **zero** external requests.
