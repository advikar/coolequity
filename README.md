# CoolEquity

**Which neighborhoods should a city cool first?** A heat-equity engine that scores
every hex in a city on satellite heat, tree canopy, population, age and walking
distance to relief — then prices the intervention.

> **This is the `san-ramon` branch.** It runs on **San Ramon, California**: 540
> hexes at H3 resolution 9 (~0.11 km² each) covering all 52 km² inside the city
> limits, 85,150 residents. The Los Angeles build lives on `master` and is
> untouched by this branch — every artefact here is suffixed `_sanramon`, so the
> two sets of data files coexist rather than overwrite each other.

Every input except the US redlining overlay is global (Landsat, Sentinel-2,
OpenStreetMap, a population grid), so the same pipeline runs on any city. San
Ramon is the proof: retargeting was a config change plus four genuinely
city-specific fixes, all documented below.

**Live (Los Angeles, from `master`): <https://advikar.github.io/coolequity/>** — served by GitHub Pages from
`master`. Pages serves the repo root, which is the same thing `python3 -m
http.server` does locally, so `app/` finds `../data/` unchanged. The root
`index.html` is only a redirect into `app/`; `.nojekyll` stops Pages' Jekyll
step from dropping underscore-prefixed paths like `data/_cache/`.

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

Point at another city by editing `CITY`, `SLUG`, `BBOX`, `H3_RES`, `RASTER_CRS`,
the county FIPS and `CLIP_URL` in `pipeline/config.py`. Outside the US,
`03_census.py` needs a WorldPop path and `04_overlays.py` will find no HOLC map —
the overlay is US-only by construction.

### What retargeting to San Ramon actually took

Worth reading before you point this at a third city, because none of these were
predictable from the LA build and all four are the kind of thing that fails
quietly:

1. **One summer was not enough imagery.** Summer 2023 over San Ramon's small
   footprint yields exactly **one** Landsat scene under the 20% cloud filter — a
   single afternoon, not a median. The window is now the summer months of
   **2022, 2023 and 2024** at the same strict cloud threshold, giving 9 Landsat
   and 11 Sentinel-2 scenes. `02_satellite.py` searches each year separately and
   concatenates; a continuous `2022-06-01/2024-09-15` range would have pulled in
   January scenes and turned a summer thermal median into an annual mean.
2. **Resolution had to go up, and that has a cost.** At res 8 a 52 km² city is
   71 hexes. Res 9 gives 540 and a real map — but San Ramon holds only ~55
   census block groups, so a hex is about a *ninth* of a block group. Heat and
   canopy are genuinely measured per hex (30 m rasters); **population, age and
   income are interpolated downward** and vary smoothly across neighbours. Real
   data, coarser than the grid drawn over it. The app says so.
3. **A/C access had to leave the score.** See below.
4. **The hex names were unusable.** LA had plenty of OSM place nodes; San Ramon
   has five, which produced "Windemere NE 19". It does have **90 named
   residential subdivisions** mapped as landuse polygons, so `04_overlays.py`
   now names a hex after the subdivision it falls *inside* (`NAME_FROM_LANDUSE`),
   falling back to the nearest non-park anchor. Parks are excluded from the
   proximity pass — there are 49 in 52 km² and they otherwise won every contest,
   giving every third hex a name like "Piccadilly Square Park E 5".

## How the score works

Each input is min–max normalized **within the city** — 44 °C is ordinary in
Phoenix and alarming in Seattle, and normalizing locally is what makes the score
portable.

```
base_risk = 0.45·heat + 0.33·(1 − canopy) + 0.22·age65
priority  = base_risk · (0.55 + 0.45 · population)
score     = 100 · minmax(priority)
```

**A/C access carries 0% here, and that is the most important difference from the
LA build.** It is not measured anywhere — it is modelled by ranking each hex's
median household income *within the city* and mapping that percentile onto a
35–95% range. In LA that percentile carries real signal, because block-group
medians span roughly $20k to $250k. San Ramon's span **$101,645 to $250,001** —
narrow and uniformly high. Running the same transform over that band would paint
a 35%-to-95% spread of "A/C access" across a city where essentially everyone can
afford it, and then hand that invented variation a quarter of the score. So the
layer is still built from real ACS income and can still be viewed on the map, and
it is weighted zero. LA's 35/25/15 renormalises to 45/33/22 once it leaves.

The practical upshot: **every input the San Ramon score actually uses is
measured, not modelled.**

**The weights are not buried in a config file.** The app opens on six named
presets — *Pipeline default*, *Heat first*, *Shade gap*, *Protect seniors*, *No
relief nearby*, *Most people* — and each one re-scores and re-ranks all 540 hexes
in the browser, with the map, ranked list, legend copy and ROI all following. The
sliders are one click away under **Adjust the weights yourself**. (LA's *A/C
poverty* preset is gone here; leaning a preset on the one input weighted zero for
good reason would be theatre.)

The app exposes an **input the pipeline does not use**: walking time to
relief, shipped at weight 0. It is the one input describing what a resident can
do about the heat today, before any tree is planted, and in LA it cuts against
the other four — but a non-zero default would make "Pipeline default" a lie
about `config.py`, and would break the parity check below. *No relief nearby* is
the preset that turns it on, at 20%.

Presets lead rather than sliders because the weights are normalised to 100%:
moving a single slider is largely absorbed by the others, so it reorders a pair
of neighbours instead of visibly changing the answer. Setting all of them at once
is what makes the question legible. Checked live against `LIVE.rank`, the top hex
moves with the question asked:

| Preset | #1 hex |
|---|---|
| Pipeline default | Fairway Village Apartments SE |
| Heat first | Fairway Village Apartments SE |
| Shade gap | Fairway Village Apartments SE |
| Protect seniors | **Amador Lakes Apartments N** (39.8% aged 65+) |
| No relief nearby | **Canyon Oaks** |
| Most people | **Canyon Oaks** (707 residents) |

It is the same model, not a demo approximation — the browser runs the same
arithmetic as `pipeline/05_score.py` against the committed `data/sanramon.geojson`,
and any residual is that geojson storing `lst`/`green`/`ac` at one decimal place.
The pipeline's own `score` and `rank` are never overwritten, so Reset is exact.

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
  as `est.` **It carries 0% of the score in San Ramon**, deliberately; see the
  scoring section above. It is still on the map as a viewable layer.
- **Population, age and income are interpolated below block-group resolution.**
  A res-9 hex is roughly a ninth of a census block group, so those three fields
  are real ACS figures spread by area, not measured per hex. They vary smoothly
  across neighbouring hexes and you can see it on the map. Heat and canopy do
  not have this problem — they are 30 m satellite rasters averaged per hex.
- **Walk time is not routed.** Straight-line distance × 1.273 (= 4/π, the exact
  expected Manhattan-to-Euclidean ratio over uniform bearings) at 4.8 km/h. The
  right correction for a gridded city; still an estimate. Say "estimated walking
  minutes."
- **Canopy % is an NDVI proxy**, NDVI 0.05–0.65 scaled to 0–45%. Vegetation, not
  strictly tree crown.
- **1 uninhabited hex is dropped**, so the map has real holes over the bay,
  Griffith Park and the Sepulveda Basin. They'd otherwise invert the headline
  heat/greenness correlation and stretch the ramp over a range nobody lives in.
- **Coverage is the incorporated city of San Ramon**, clipped to the TIGERweb
  place polygon for GEOID 0668378 — not the Tri-Valley, and not Contra Costa
  County. The ragged edges are the real city limits, which are ragged: San Ramon
  annexed in pieces and Dougherty Valley hangs off the east side. Bishop Ranch,
  Danville and Dublin are outside by construction.
- **There is no redlining layer, and that is history rather than a missing
  file.** HOLC surveyed built-up cities in 1935–40. San Ramon was farmland then
  and did not incorporate until 1983, so Mapping Inequality has no map for it —
  they have Oakland, Berkeley, Richmond, San Francisco, San Jose and Stockton.
  The app hides the toggle when no hex carries a grade and says why, rather than
  borrowing a neighbouring city's grades.
- **Only San Ramon has been through the pipeline on this branch.** The landing
  screen's city search says so: every other city is marked *pipeline-ready* and
  shows what building it takes. Los Angeles is listed **without** a `have` flag,
  because although it is built on `master`, its data files are not on this
  branch — claiming it here would be exactly the lie the list exists to prevent.
  The `have` field is the single thing that decides whether the button opens a
  dataset.
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

Holding up: across the 540 populated hexes, heat and greenness correlate at
**r = −0.797** — stronger than LA's −0.61, and in a city with no coastline to
confound it.

## Repo

```
app/index.html        the whole front end
app/vendor/           MapLibre 4.7.1 (BSD-3) + Inter & Instrument Serif (OFL 1.1),
                      all vendored so the page makes no off-host requests
pipeline/             01→05, run in order; config.py holds bbox, weights, constants
data/                 committed outputs, all suffixed _sanramon so the LA files
                      on master are never overwritten; the app needs
                      sanramon.geojson + centers_sanramon.geojson
DEMO.md               the 60–90s script, with real numbers and the likely questions
SPEC.md               the original build spec; Section 10 superseded by DEMO.md
STATUS.md             build state, fixed bugs, decisions taken
```

## Provenance

USGS/NASA **Landsat 8/9** thermal (ST_B10 → °C) and ESA **Copernicus Sentinel-2**
NDVI, medians over the summers of 2022–2024 via Microsoft **Planetary Computer** ·
**US Census ACS** 2023 5-year for Contra Costa County, block groups area-weighted
into hexes · city limits from **US Census TIGERweb** (place GEOID 0668378) ·
**OpenStreetMap** contributors (cooling sites, subdivision and park names) via
Overpass · tree-cooling coefficient from **WRI**, *Cooling Potential of Urban
Trees* · **H3** hex grid (Uber) · basemap © CARTO. No HOLC layer — see above.
