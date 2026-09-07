# CoolEquity — every feature, its data source, and its limitations

A complete reference for what the map does, where each number comes from, and what
it can and cannot be trusted to say. Written for a city team. Read this next to
`DATA_QUALITY.md` (the prioritised caveat audit) — this file is the inventory,
that one is the fix list.

**Cities live:** Los Angeles `/app/`, San Ramon `/sanramon/app/`, Contra Costa
County `/contracosta/app/`, Bakersfield `/bakersfield/app/`, chooser at the root.
Where a row says "SR/CC/Bak" it means all cities *except* LA, which runs an older
pipeline (see the LA notes at the end).

---

## 1. Map layers (the "Map layer" buttons)

| Layer | What it shows | Source | Key limitations |
|---|---|---|---|
| **Priority** (composite) | Where to cool first: a 0–100 score per residential hex | Computed: `base = w_heat·heat + w_green·(1−canopy) + w_ac·(1−ac) + w_age·age65`, then `× (0.55 + 0.45·pop)`, min-max→0–100 | **Relative within one city, not an absolute hazard** and not comparable between cities. Weights are chosen, not calibrated to a health outcome (none exists at this geography). Recomputed live from the sliders. |
| **Surface heat** | Summer daytime land-surface temperature | **Landsat 8/9** thermal (ST_B10), median of summers 2022–24, via Microsoft Planetary Computer | **Surface ≠ air temperature.** Landsat crosses ~10:30–11:30 local — **mid-morning, not the afternoon peak.** **Weighted 0 in CC & SR** (absolute temp there mostly tracks distance from the Bay, not need). |
| **Tree canopy** | % of ground under tree canopy | **USFS/CAL FIRE 2022** aerial canopy (0.6 m NAIP) for SR/CC/Bak; rural fringe outside the urban-area boundary falls back to the Meta/WRI CHM. **LA: still Sentinel-2 NDVI proxy.** | Canopy **extent, not a tree count/inventory** (CS-1b's inventory still needs LiDAR/ground). 2022 vintage. Fringe hexes mix two sources. LA overstates (NDVI counts lawn). |
| **Lawn / non-tree vegetation** (`veg`) | Photosynthesising ground that is *not* tree canopy | **Sentinel-2** NDVI, summer medians 2022–24 | An NDVI proxy — counts irrigated lawn, crops, shrub. Useful as "green but unshaded = cheap place to plant," not as canopy. |
| **Population exposed** | Residents per hex | **US Census ACS 2023 5-year**, block groups apportioned into hexes | Interpolated, not counted. Dasymetric (by building floor area) where OSM coverage is good (SR); **area-weighted in CC** (OSM maps its rich block groups 4.7× better, so building-weighting would demote poor areas). Block groups are ~3.6–9× a hex. |
| **Age 65+** | Share of residents 65+ | ACS 2023, empirical-Bayes shrunk toward the citywide rate | Smoothed (a 4-person hex can't read 100% elderly) and interpolated; not block-precise. |
| **A/C access** | % of occupied homes with air conditioning | **US Census LACE 2023** (Local A/C Estimates), tract level — *measured*, replacing the old income proxy | Tract-level (coarser than a hex). **Counts any A/C including evaporative ("swamp") coolers**, which protect far less in extreme heat — flagged on the Bakersfield layer. Income-model fallback only where a tract is suppressed (`ac_src` records which). |
| **Walk to cooling relief** | Est. walking minutes to the nearest cooling site | Straight-line hex-centroid→nearest site × **1.273 circuity** ÷ 4.8 km/h; sites from **OpenStreetMap** | **Not a routed path** — ignores freeways, rivers, walls. OSM cooling sites aren't verified as *designated, open, air-conditioned* cooling centres. Labelled "est." |
| **Redlining (HOLC)** | 1930s HOLC grades A–D | **Univ. of Richmond, Mapping Inequality** | **LA only** (SR/Bak/most of CC were farmland in 1935; the toggle hides itself where no hex is graded). Historical context, not current condition. |

## 2. The three land classes (every hex is now shown — `place` property)

| Class | Meaning | How decided | Shown as |
|---|---|---|---|
| **res** | Has residents | ACS population ≥ 1 | Scored & ranked (colour ramp) |
| **activity** | Developed, ~no residents (commercial/industrial/institutional) | ≥120 m street frontage **OR** ≥3 buildings **OR** (≥40 m road AND ≥1 building), from OSM streets + 02b footprints | Real canopy/heat on those layers; **grey on Priority; not ranked** |
| **empty** | Undeveloped | none of the above | **Muted fill + border**, with a best-effort `land` label |

**`land` labels for empty hexes** (open water / woodland / open land / bare hillside) are inferred from the satellite layers (cool+unvegetated → water, high canopy → woodland, etc.). **Validated against ESA WorldCover 10 m: 92% agreement on Contra Costa**, remaining 12/156 are minor (bare-vs-open-land). Labelled "likely" in the UI. *Upgrade path: pull ESA WorldCover / NLCD directly for authoritative labels — mechanism proven, see the handoff.*

## 3. Interactive functions

| Function | What it does | Source / basis | Limitations |
|---|---|---|---|
| **Weight sliders + presets** | Re-score & re-rank live as you change what counts | Same formula as the pipeline, recomputed in-browser; parity with the pipeline < 0.1 pts | Live score stored at 1–2 dp; residents-only (activity/empty excluded from ranking). |
| **ROI planting calculator** (detail panel) | Trees, cost, cooling, residents helped for a canopy target | WRI *Cooling Potential of Urban Trees* (+10% canopy ≈ −0.3 °C afternoon air temp); **$500/tree** and **40 m²/crown** are *planning assumptions*; street-frontage capacity at 10 m spacing both sides | Cost is order-of-magnitude, not a bid. Cooling coefficient is a generalised literature value applied uniformly (air-temp, vs surface-temp heat layer). Capacity ignores driveways/utilities. |
| **City switcher / "All cities"** | Move between the four deployed cities / the chooser | Static links under the Pages root | Replaced the old fake 20-city search. Only the four built cities are real. |
| **Metric / imperial toggle** | °C·km ↔ °F·mi | Display only | Temperature *deltas* convert as differences, not absolutes. |
| **Detail panel** | Per-hex score breakdown + all metrics + ROI | The hex's own properties | Activity/empty hexes show canopy/heat + a "not ranked" note instead of a score. |
| **Hover tooltip** | Name, priority, heat, canopy, walk time | Live values | Trusts the live score over the frozen property. |
| **Home / flat basemap (`?flat=1`)** | Reset to the city intro / render with zero off-host requests | Local vendored MapLibre + fonts; CARTO positron basemap otherwise | Flat path draws the boundary + hexes only (venue-Wi-Fi fallback). |
| **Cooling-site categories** | Filter libraries / community centres / pools / senior sites | `kind` in `centers_<city>.geojson` (OSM) | See walk-time caveats. |

## 4. Backend / pipeline (per city, `pipeline/`)

| Step | Produces | Source | Notes |
|---|---|---|---|
| `01_make_grid` | H3 grid | H3 (res 8 for LA/CC ≈ 0.77 km²; res 9 for SR/Bak ≈ 0.11 km²) | Hex ≠ census block. Areas geodesic (correct). |
| `02_satellite` | LST, NDVI rasters/CSV | Landsat 8/9 + Sentinel-2, Planetary Computer | Per-summer search (never a continuous range). Sentinel BOA offset applied. Per-tile scene budget (a county-scale bug fixed). |
| `02b_buildings` | Residential footprints | OpenStreetMap | Coverage varies; drives the dasymetric guard. |
| `02d_canopy_usfs` | Measured canopy | USFS/CAL FIRE 2022 (EPSG:3310 equal-area, per-hex windowed reads, urban-boundary denominator) | Fixes the old web-Mercator area bug + nodata handling. CHM fallback for fringe. |
| `03_census` | pop, age, income, A/C | ACS 2023 + **LACE 2023** join | Dasymetric-safety guard (refuses building-weighting when OSM is incomplete/biased). |
| `04_overlays` | cooling sites, walk time, street_m, names, HOLC | OpenStreetMap + Mapping Inequality | Overpass rate-limited; walk time is circuity-adjusted straight line. |
| `05_score` | the app's geojson | fuses all of the above | One-sided p2/p98 clip so outliers don't set the scale; three-class `place`; `norm` written for exact app parity. |
| `deploy.sh` | assembles `gh-pages` from all four branches | — | **Pushing a source branch does NOT update the site — run `./deploy.sh`.** Now: always `node --check` each app first. |

## 5. Los Angeles — what's different (deliberately not modernised this round)

LA runs the original, older pipeline: **canopy is still the Sentinel-2 NDVI proxy** (overstates cover), CSV filenames are unslugged, and `05_score` predates the measured-canopy contract, so LA is **not** on the three-class land model (it still drops unpopulated hexes). LA *did* get measured LACE A/C. The recipe to bring LA up to parity (USFS canopy + three-class) is in `DATA_QUALITY.md` follow-up 1.

## 6. Known-broken-then-fixed (for the record)

Two of this session's own edits shipped syntax errors that made the **SR and LA apps blank/dead live** (an unescaped apostrophe; a missing brace) before they were caught and fixed. `node --check` on every app is now part of deploy. If an app ever renders blank, syntax-check its inline `<script>` first.
