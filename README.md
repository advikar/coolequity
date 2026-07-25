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

**This works with no network at all.** MapLibre and both typefaces are vendored
in `app/vendor/` and every data file is local; without internet you lose only
the CARTO street basemap, and the map falls back to a flat background with the
county outline drawn in. Rehearse that look at `/app/?flat=1`, which should make
**zero** off-host requests.

Other URL switches: `?go=1` skips the landing screen and opens straight onto the
map; `?data=<name>` swaps the hex file (`?data=grid` for the unscored grid, or
point it at another city's output) and implies `?go=1`.

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
portable.

```
base_risk = 0.35·heat + 0.25·(1 − canopy) + 0.25·(1 − ac_access) + 0.15·age65
priority  = base_risk · (0.55 + 0.45 · population)
score     = 100 · minmax(priority)
```

**The weights are not buried in a config file.** The app opens on seven named
presets — *Pipeline default*, *Heat first*, *Shade gap*, *Protect seniors*, *A/C
poverty*, *No relief nearby*, *Most people* — and each one re-scores and re-ranks
all 3,008 hexes in the browser, with the map, ranked list, legend copy and ROI
all following. The sliders are one click away under **Adjust the weights
yourself**.

The app exposes a **fifth input the pipeline does not use**: walking time to
relief, shipped at weight 0. It is the one input describing what a resident can
do about the heat today, before any tree is planted, and in LA it cuts against
the other four — but a non-zero default would make "Pipeline default" a lie
about `config.py`, and would break the parity check below. *No relief nearby* is
the preset that turns it on, at 20%.

Presets lead rather than sliders because the weights are normalised to 100%:
moving a single slider is largely absorbed by the other three, so it reorders a
pair of neighbours instead of visibly changing the answer. Setting all four at
once is what makes the question legible. *Protect seniors* drops Westlake from
#1 to #5 and lifts Holmby Hills — one of the wealthiest zip codes in America —
from roughly 2,100th to 27th. (Holmby Hills only reaches #1 under a pure 100%
age weighting, which no preset uses.)

*No relief nearby* is the counter-example worth knowing: it barely moves the top
ten, because the population multiplier keeps the dense inner-city blocks in
front and those blocks are already close to libraries. What it does move is the
middle — 722 of 3,008 hexes shift by more than a hundred places.

It is the same model, not a demo approximation. Checked in-page against the
committed `data/la.geojson` at the shipped weights: **max absolute difference
0.156 points, mean 0.039, and pipeline ranks #1–#6 reproduced exactly** — the
residual is the geojson storing `lst`/`green`/`ac` rounded to 1 dp. The
pipeline's own `score` and `rank` are never overwritten, so Reset is exact.

Defaults live in `pipeline/config.py` and are mirrored in the app's `DEFAULT_W`
and in the `default` entry of `PRESETS`; keep those in sync. `normW()` and
`matchPreset()` fold over `W_INPUTS`, so adding a sixth input is one array entry
rather than an edit in five places. The legend prose and
the preset state chip are generated from the weights in force, so they cannot
drift.

Selecting a hex shows the arithmetic term by term — what each input measured,
where that sits on the city's 0–1 scale, what the weight turns it into, and how
the four add up before population scales them.

### Reading the map

One rule across every layer, restated in the legend under the colour bar:
**deeper and more saturated = more need for cooling investment.** Every ramp's
pale end starts *darker than the `#eceff3` basemap*, so a low-scoring hex still
reads as a hexagon rather than as a hole in the map — the low third is meant to
be quiet, not invisible. For the two
protective inputs — tree canopy and A/C access — the needy end is the *low* end,
so those ramps run deep→pale and the legend's arrow flips rather than the
meaning. The basemap is light so that the deep end is the heaviest ink on the
screen; that is what makes the rule readable at a glance.

The ROI calculator in the detail panel, per hex:

```
temp_drop_C = (target_canopy_pct − current_pct) / 10 × 0.3    # WRI coefficient
trees       = Δcanopy/100 × hex_area_m2 / 40                  # ~40 m² per mature tree
cost        = trees × $500                                    # planted + 3yr maintenance
```

All three constants are named on screen under the calculator. The WRI
coefficient is published science; the 40 m² crown is a standard planning figure;
**the $500 is an assumption, not a quote or a bid** — the order of magnitude US
municipal programmes use for a planted street tree plus about three years of
establishment care. The UI says so in those words. Real unit costs vary widely
with species, site preparation and sidewalk work.

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
- **Only Los Angeles has been through the pipeline.** The landing screen's city
  search says so: every other city is marked *pipeline-ready* and shows what
  building it takes, rather than loading LA's numbers under another name. The
  `have` field on a `CITIES` entry is the single thing that decides whether the
  button opens a dataset, so adding a city to the search list cannot fake data.
- **"Cooling site" means the four OpenStreetMap categories `04_overlays.py`
  queries** — libraries, community centres, public pools, senior centres and
  shelters. It is not a list of sites a city has formally designated as cooling
  centers on a heat day; it is the set of places a resident could plausibly walk
  to and sit in the cool for free. The app names all four and lets you switch
  each off, under **Show the four categories**.
- **The priority score is a ranking within one city, not an absolute hazard
  level.** Every input is min–max normalized locally, so a score of 100 means
  "first in line here", not "hot by world standards" — a uniformly mild city
  would still have a rank-1 hex. The legend says this outright, and the Surface
  temperature layer is the one that answers the absolute question.

Holding up: across the 3,008 populated hexes, heat and greenness correlate at
**r = −0.61**, and it survives both a longitude-band split and removing a
quadratic spatial trend (−0.58).

## Repo

```
app/index.html        the whole front end
app/vendor/           MapLibre 4.7.1 (BSD-3) + Inter & Instrument Serif (OFL 1.1),
                      all vendored so the page makes no off-host requests
pipeline/             01→05, run in order; config.py holds bbox, weights, constants
data/                 committed outputs — the app needs la.geojson + centers.geojson
DEMO.md               the 60–90s script, with real numbers and the likely questions
SPEC.md               the original build spec; Section 10 superseded by DEMO.md
STATUS.md             build state, fixed bugs, decisions taken
```

## Provenance

USGS/NASA **Landsat 8/9** thermal (ST_B10 → °C) and ESA **Copernicus Sentinel-2**
NDVI, summer 2023 medians via Microsoft **Planetary Computer** · **US Census ACS**
2023 5-year, block groups area-weighted into hexes · **OpenStreetMap** contributors
(cooling sites, place names) via Overpass · HOLC grades from the University of
Richmond **Mapping Inequality** project · tree-cooling coefficient from **WRI**,
*Cooling Potential of Urban Trees* · **H3** hex grid (Uber) · basemap © CARTO.
