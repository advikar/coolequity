# CoolEquity

**Which neighborhoods should a city cool first?** A heat-equity engine that scores
every ~0.8 km² hex in a city on satellite heat, tree canopy, population, age and
walking distance to relief — then prices the intervention. Shown here on Los
Angeles: 3,008 hexes, 6.5M residents.

Every input except the US redlining overlay is global (Landsat, Sentinel-2,
OpenStreetMap, a population grid), so the same pipeline runs on any city.

---

## Run it

The app is static. No build step, no server-side anything.

```bash
cd coolequity
python3 -m http.server 8000       # then open http://localhost:8000/app/
```

Serve from the **repo root**, not from `app/` — the page reads `../data/`.

**This works with no network at all.** MapLibre is vendored in `app/vendor/` and
every data file is local; without internet you lose only the CARTO street
basemap, and the map falls back to a flat background with the county outline
drawn in. Rehearse that look at `/app/?flat=1`.

Other URL switches: `?data=<name>` swaps the hex file (`?data=grid` for the
unscored grid, or point it at another city's output).

The app wants ~700px of map width. Below that the 366px panel crowds it out —
fine on a projector, worth knowing on a small laptop.

## Rebuild the data

Only needed if you're changing the pipeline; the committed outputs are complete.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
echo "CENSUS_API_KEY=..." > .env && chmod 600 .env    # api.census.gov/data/key_signup.html
cd pipeline
../.venv/bin/python 01_make_grid.py     # H3 res-8 grid over the bbox    → grid.geojson
../.venv/bin/python 02_satellite.py     # Landsat LST + Sentinel-2 NDVI  → satellite.csv
../.venv/bin/python 03_census.py        # ACS pop / age / income         → census.csv
../.venv/bin/python 04_overlays.py      # HOLC + cooling centres + walk  → overlays.csv
../.venv/bin/python 05_score.py         # composite score + rank         → la.geojson
```

Two flags, deliberately opposite:

- `02_satellite.py --cached` — skips the network and uses the committed rasters.
  It goes live by default.
- `04_overlays.py --refresh` — forces a live Overpass pull. It uses the cache by
  default, because Overpass rate-limits and re-pulling 645 amenities on every
  tweak is how you get 504'd an hour before a demo.

Point at another city by editing `BBOX`, `CITY` and the census settings in
`pipeline/config.py`. Outside the US, `03_census.py` needs a WorldPop path and
`04_overlays.py` will find no HOLC map — the overlay is US-only by construction.

## How the score works

Each input is min–max normalized **within the city** — 44 °C is ordinary in
Phoenix and alarming in Seattle, and normalizing locally is what makes the score
portable. Weights live in `pipeline/config.py` and are restated in the app's
legend; keep the two in sync.

```
base_risk = 0.35·heat + 0.25·(1 − greenness) + 0.25·(1 − ac_access) + 0.15·age65
priority  = base_risk · (0.55 + 0.45 · population)
score     = 100 · minmax(priority)
```

The ROI calculator in the detail panel, per hex:

```
temp_drop_C = (target_canopy_pct − current_pct) / 10 × 0.3    # WRI coefficient
trees       = Δcanopy/100 × hex_area_m2 / 40                  # ~40 m² per mature tree
cost        = trees × $500                                    # planted + 3yr maintenance
```

## What's estimated, and what isn't

Stated plainly because a judge will ask, and because the UI labels it anyway:

- **A/C access is modeled**, not measured — derived from median income and shown
  as `est.` It carries 25% of the score. It is the weakest input here.
- **Walk time is not routed.** Straight-line distance × 1.273 (= 4/π, the exact
  expected Manhattan-to-Euclidean ratio over uniform bearings) at 4.8 km/h. The
  right correction for a gridded city; still an estimate. Say "estimated walking
  minutes."
- **Canopy % is an NDVI proxy**, NDVI 0.05–0.65 scaled to 0–45%. Vegetation, not
  strictly tree crown.
- **478 uninhabited hexes are dropped**, so the map has real holes over the bay,
  Griffith Park and the Sepulveda Basin. They'd otherwise invert the headline
  heat/greenness correlation and stretch the ramp over a range nobody lives in.
- **Coverage is the LA basin, not LA County** — 6.5M of the county's 9.85M. The
  hard straight edge near El Monte is the bbox, not missing data.

Holding up: across the 3,008 populated hexes, heat and greenness correlate at
**r = −0.61**, and it survives both a longitude-band split and removing a
quadratic spatial trend (−0.58).

## Repo

```
app/index.html        the whole front end; app/vendor/ is MapLibre 4.7.1 (BSD-3)
pipeline/             01→05, run in order; config.py holds bbox, weights, constants
data/                 committed outputs — the app needs la.geojson + centers.geojson
DEMO.md               the 60–90s script, with real numbers and the likely questions
STATUS.md             build state, fixed bugs, decisions taken
```

## Provenance

USGS/NASA **Landsat 8/9** thermal (ST_B10 → °C) and ESA **Copernicus Sentinel-2**
NDVI, summer 2023 medians via Microsoft **Planetary Computer** · **US Census ACS**
2023 5-year, block groups area-weighted into hexes · **OpenStreetMap** contributors
(cooling sites, place names) via Overpass · HOLC grades from the University of
Richmond **Mapping Inequality** project · tree-cooling coefficient from **WRI**,
*Cooling Potential of Urban Trees* · **H3** hex grid (Uber) · basemap © CARTO.
