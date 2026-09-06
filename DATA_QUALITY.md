# CoolEquity — data-quality audit

*Every approximation, caveat, and known error in the pipeline, with a concrete fix for each.*
Written to be read by a GIS analyst or a city sustainability team, not just the build. If a
figure from this tool is going into a grant application or a planting plan, read the item that
governs it first.

**How to read the priority column.** **P1** materially changes *which blocks rank where* or
*what the headline number is* — fix before the tool is used to allocate money. **P2** affects
accuracy at the margin or is a disclosed limitation with a real upgrade path. **P3** is latent,
cosmetic, or already honestly labelled.

The single most valuable change on this list is **C-1 (replace the canopy source)**. The
second is **AC-1 (replace the modelled A/C layer with measured data)**. Both are described in
full at the bottom, with sources.

---

## A. Canopy — the headline metric

| # | Issue | Impact | In-app now | Fix |
|---|---|---|---|---|
| **C-1** | **Vintage.** Canopy comes from the Meta/WRI Canopy Height Map, built from **2009–2020** Maxar imagery — up to 16 years old, and older than the 2022–24 heat and 2023 census it is scored against. | **P1.** Trees planted or lost since ~2015 are invisible. Worst in fast-changing areas: Dougherty Valley (San Ramon) and new Bakersfield subdivisions were built or matured after the imagery. A block can read "bare" because the canopy postdates the data. | Disclosed as "Meta/WRI canopy height," vintage not stated on the map. | **Replace with USFS/CAL FIRE 2022 California Urban Tree Canopy** (0.6 m, NAIP-derived, CC0). See §C-1 below. Biggest accuracy gain available. |
| **C-2** | **Systematic low bias.** The height model reads ~38 % below professional aerial assessment (9.1 % vs Fresno's published 14.6 % over the same boundary). | **P1** for absolute claims, **P2** for ranking. The tool ranks blocks correctly but its canopy % cannot be quoted as the real coverage. | Disclosed: "ranks blocks; does not certify absolute canopy." | The USFS 2022 product **is** the aerial-grade classification, so the bias largely disappears and canopy % becomes citable in absolute terms. Removes this caveat. |
| **C-3** | **Height threshold, not crown detection.** Anything ≥ 2 m of vegetation counts as canopy; a smooth modelled height surface merges touching crowns, so no honest per-tree count is possible. | **P2.** Tall hedges and shrubs count as canopy; deliberately no tree count (correct call). | Disclosed at length; no tree count shipped. | The USFS product is a canopy / no-canopy classification from imagery, not a 2 m height cut, so it is closer to what "canopy" should mean. Keep the no-tree-count discipline. |
| **C-4** | **Web-Mercator area distortion.** `02c_canopy.py` works in EPSG:3857; at 37–38° N a Mercator "metre" is ~1.25× a real metre, so Mercator **area** is inflated ~1.56×. This inflates the exported `row_m2` (plantable public right-of-way). | **P2 latent.** `canopy_pct` is a pixel *ratio* so it cancels — **unaffected**. `canopy_m2` uses the geodesic hex area — **unaffected**. Only `row_m2` is wrong, and the app's ROI panel uses real-metre `street_m` instead, so **no user-facing number is affected today**. But the exported column is ~1.5× too high. | Not surfaced. | Do the canopy zonal stats in `RASTER_CRS` (UTM 10N) like the rest of the pipeline, or scale `row_m2` by cos²(lat). One-file fix. |
| **C-5** | **NoData counted as "no canopy."** Every pixel in a hex goes into the denominator; nodata (tile edges, water) is treated as un-canopied, biasing canopy low where nodata is present. | **P3.** Small for inland CA cities; larger for coastal/edge hexes. | Not surfaced. | Mask the CHM nodata value before the ratio. |
| **C-6** | **Read decimation** to 1.2 m (cities) / 2.4 m (counties) from 0.6 m native. | **P3.** Tested to move canopy ~1 pt, inside the product's own bias. | Not surfaced. | None needed; note it. Moot after C-1. |

## B. Heat — land surface temperature

| # | Issue | Impact | In-app now | Fix |
|---|---|---|---|---|
| **H-1** | **Surface ≠ air temperature.** Landsat measures land-surface (skin) temperature; people experience air temperature, which is less extreme and less variable. | **P2.** A 51 °C surface reading is not a 51 °C air reading. | Layer is labelled "surface temperature." | Keep the label explicit. Air-temp modelling is possible but heavy; not worth it for a ranking tool. |
| **H-2** | **Overpass timing.** Landsat 8/9 cross at ~10:30–11:30 local — **mid-morning, not the afternoon peak.** The ROI text cites WRI's *afternoon* cooling coefficient. | **P2.** The heat layer and the ROI cooling claim are anchored to different times of day. | ROI says "afternoon"; heat layer does not state the time. | Relabel the heat layer "mid-morning surface temperature," and/or add an afternoon/evening source — **ECOSTRESS** (ISS, variable overpass incl. afternoon & night) is the standard complement. |
| **H-3** | **Summer median** over 2022–24, scenes < 20 % cloud, emissivity from the C2-L2 ST product. | **P3.** Sound method; the summer-per-year search (not a continuous range) is deliberate and correct. | Provenance shown. | None. Keep the per-summer search — a continuous date range would pull winter scenes into a "summer" median. |
| **H-4** | **Heat weighted 0** in Contra Costa and San Ramon (absolute temperature across a marine-to-inland county mostly tracks distance from the Bay, not local need). | **P2 by design.** A user may expect the hottest blocks to rank highest; they don't, because heat is unscored there. | Disclosed in the legend and the ROI "why cooling is claimed when heat isn't scored" note. | Defensible and documented. Leave as a user-adjustable weight. |

## C. A/C access

| # | Issue | Impact | In-app now | Fix |
|---|---|---|---|---|
| **AC-1** | **Modelled, not measured.** `ac_est = 35 % + 60 % × income-rank-percentile`. It is a relabelled income rank, nothing more. | **P1** where scored: **weighted 0.25 in Contra Costa** (moves the ranking), 0 in San Ramon. | Labelled "modelled / est." throughout. | **Replace with measured tract-level A/C prevalence.** See §AC-1 below. |
| **AC-2** | **Circularity.** Because `ac_est` *is* income and A/C is 25 % of the Contra Costa score, the ranking partly tracks income by construction. | **P1.** "Priority tracks income" must never be presented as an independent finding for CC. | Noted in `FINDINGS_CONTRACOSTA.md`; the landing-page income finding is computed on raw canopy, which is clean. | Real A/C data (AC-1) breaks the circularity and lets the income relationship be tested honestly. |

## D. Population, age, income (ACS)

| # | Issue | Impact | In-app now | Fix |
|---|---|---|---|---|
| **D-1** | **Apportionment.** ACS block groups (~3.6× a hex) are split into hexes by residential floor area (dasymetric where OSM buildings are complete) or by ground area (fallback). Demographics vary *smoothly*, not per block. | **P2.** Per-hex population/age/income are interpolations, not counts. The dasymetric guard (ACS reconciliation to 0.2 %) keeps totals honest, but a single hex's pop is an estimate. | Disclosed on the landing screen. | Use **2020 Census blocks** (decennial, exact counts, ~10× finer than block groups) as the dasymetric population target instead of area/floor. Removes most interpolation error for population. |
| **D-2** | **Averaging medians.** Hex income is a floor-/area-weighted **mean of block-group median incomes** — statistically improper (a weighted mean of medians is not a median). | **P3.** Small bias; income only feeds the A/C proxy, which AC-1 replaces anyway. | Not surfaced. | Assign each hex the median of the block group it mostly overlaps, rather than averaging across overlaps. |
| **D-3** | **ACS margins of error** are not propagated. Block-group income and age MOEs are large; suppressed values are handled but uncertainty is dropped. | **P3.** A ±estimate presented as a point value. | Not surfaced. | Carry the MOE columns; optionally grey out hexes whose driving estimate has a CV above a threshold. |
| **D-4** | **Age-65 empirical-Bayes shrinkage** (100-person pseudo-count) pulls small-hex rates toward the city mean. | **P3, by design.** Prevents a 4-person hex reading 100 % elderly; costs some real signal in small hexes. | Disclosed. | Sound. Leave as is. |

## E. Cooling access / walk time

| # | Issue | Impact | In-app now | Fix |
|---|---|---|---|---|
| **W-1** | **Not routed.** Walk time is a straight line from the hex centroid to the nearest cooling site × 1.273 circuity ÷ 4.8 km/h. It ignores freeways, rivers, rail, walls and actual sidewalks. | **P2.** A hex one freeway away from a site reads "close." | Labelled "estimated walking minutes, not a routed path." | Route on the OSM pedestrian network (**OSRM** or **Valhalla** foot profile) — accurate door-to-door minutes, and it respects barriers. Heavier but well within reach for four cities. |
| **W-2** | **Cooling sites from OSM tags.** Completeness varies, and an OSM "community centre" or "library" is **not** necessarily a designated, open, air-conditioned cooling centre during a heat event. | **P2.** The denominator of "relief nearby" may be wrong in both directions. | Sites are classified and counted from the file; designation is not claimed. | Use the **county/city official cooling-centre list** (and its hours) as the authoritative layer; keep OSM as a fallback. |
| **W-3** | **`access_min` filled with the median** for hexes with no reachable site — masks true isolation as "average." | **P3.** Under-flags genuinely stranded blocks. | Not surfaced. | Represent "no site within N minutes" explicitly rather than imputing the median. |

## F. Scoring / normalisation

| # | Issue | Impact | In-app now | Fix |
|---|---|---|---|---|
| **S-1** | **Relative, within-city.** Score is a 0–100 rank inside one city (now via one-sided p2/p98 clip). Not an absolute hazard level; **not comparable between cities.** | **P2 by design.** "#1 in Bakersfield" ≠ "#1 in San Ramon" on any absolute scale. | Disclosed in the legend. | Correct for the stated purpose. If cross-city comparison is ever needed, add an absolute index alongside the rank. |
| **S-2** | **Percentile choice.** The p2/p98 clip is a judgment call; endpoints are written into the geojson `norm` so the app reproduces the pipeline exactly, but 2/98 itself is not sacred. | **P2.** Reasonable and documented; a different percentile would reshuffle the mid-list slightly. | The clip is applied; endpoints shipped. | Sound. Revisit only with a calibration target (S-3). |
| **S-3** | **Weights are chosen, not calibrated.** 0.55 / 0.25 / 0.20 etc. are not fit to any heat-health outcome, because none exists at this geography (California publishes heat-ED rates only at **county** level). | **P2.** The weighting is defensible, not empirical. | Disclosed; the user can move every weight live. | If ZIP/tract heat-morbidity is ever obtained (HCAI Limited Data Request), calibrate weights against it. Until then, live sliders are the honest answer. |

## G. Geometry / mapping

| # | Issue | Impact | In-app now | Fix |
|---|---|---|---|---|
| **G-1** | **"Blocks" are H3 hexes, not census blocks.** CS-1b literally asks about "census blocks." Resolutions also differ by city (res 8 ≈ 0.77 km² for LA/CC; res 9 ≈ 0.11 km² for SR/Bakersfield), so hex "blocks" are not comparable across cities. | **P2.** A planner may expect census geography; the word "block" invites that. | Area/scale note in the footer. | Call them "cells / hexes," and/or offer a census-block-group or tract roll-up for anyone who needs to join to official geography. |
| **G-2** | **Hex names** come from OSM place/landuse polygons, else the nearest anchor with a compass suffix ("Valencia S"). A hex named for the nearest landmark may not *be* that development. | **P3.** Labels are approximate locators, not authoritative place names. | Compass suffixes signal approximation. | Fine; keep labelling them as locators. |
| **G-3** | **Basemap is CARTO positron** (external). `?flat=1` renders with no basemap and zero off-host requests. | **P3.** Disclosed; offline fallback exists and is tested. | Yes. | None. |
| **G-4** | **Boundary intersection overhang.** Hexes are kept if they *intersect* the city limit, so geometry overhangs into neighbours; population is clipped to the limit but the hex shape is not. | **P3.** Cosmetic edge effect; totals are correct. | Not surfaced. | Optionally clip display geometry to the boundary. |

## H. ROI / cost

| # | Issue | Impact | In-app now | Fix |
|---|---|---|---|---|
| **R-1** | **$500 / tree** planted incl. ~3 yr establishment — a planning assumption, not a bid. | **P3.** Order-of-magnitude only. | Explicitly labelled a planning assumption. | None; keep it labelled. |
| **R-2** | **WRI cooling coefficient** (+10 % canopy ≈ −0.3 °C afternoon air temp) applied uniformly to every block regardless of local climate/geometry, and it is an **air-temp** figure applied where heat is measured as **surface** temp. | **P2.** A generalised literature value, not a local measurement; and see H-2 on the time-of-day mismatch. | Sourced to WRI; the surface-vs-air distinction is spelled out in the ROI note. | Present as an order-of-magnitude planning figure (it is). If local calibration is ever available, use it. |
| **R-3** | **Frontage capacity** = both sides, 10 m spacing — ignores driveways, utilities, sight lines, existing trees. | **P3.** Explicitly an upper bound. | Disclosed. | None; labelled as an upper bound. |
| **R-4** | **40 m² / crown** to convert a canopy deficit into a tree count for the ROI. | **P3.** An assumption, but a capacity estimate (area ÷ crown), not a detection. | Sourced. | None. |

---

## §C-1 — Recent canopy data (the answer to "something this old raises flags")

**Yes, and it is free, recent, and better on every axis.**

**USFS Pacific Southwest / CAL FIRE — California Urban Tree Canopy (2022).**
- **0.6 m** resolution, derived from **2022 NAIP** aerial imagery with a deep-CNN classifier, produced with CAL FIRE, NOAA Office for Coastal Management and USFS State & Private Forestry.
- Covers **all US-Census urban areas in California** — includes Los Angeles, Bakersfield, and the Bay Area urban areas that contain San Ramon and central Contra Costa (Concord–Walnut Creek etc.).
- Ships **% canopy 2022, canopy acreage, % canopy 2018, and 2018→2022 change** — the change layer is exactly what CS-1b needs to show progress over time.
- **CC0 1.0 public domain.** Per-city and statewide GIS downloads via Box.
- Landing page: <https://www.fs.usda.gov/r05/state-private-tribal/california-urban-canopy-data>

Why it beats the current Meta/WRI CHM here: **2022 vs 2009–2020** imagery, a purpose-built **urban canopy classification** rather than a height proxy (kills the ~38 % low bias, C-2), and a **built-in change product**. Adopting it fixes C-1, C-2 and C-3 at once and lets us state absolute canopy percentages a city can defend.

Other options considered: **NLCD Tree Canopy Cover** (annual but 30 m and forest-oriented — reads ~2 % urban, unusable); **ETH Global Canopy Height 2020** (10 m, global, still a height proxy); **Meta 1 m global 2024** (same family as now — imagery still 2018–2020); commercial **EarthDefine CHM/TreeMap** (0.6 m, refreshed annually, but paid). For a California city the free USFS/CAL FIRE 2022 layer is the right default; a city with its own recent **LiDAR** (USGS 3DEP) can do better still for a definitive inventory.

Sources:
- USFS California Urban Canopy Data — <https://www.fs.usda.gov/r05/state-private-tribal/california-urban-canopy-data>
- "Sub-meter tree height mapping of California using aerial images and LiDAR-informed U-Net" — <https://www.sciencedirect.com/science/article/pii/S003442572400110X>
- EarthDefine CHM (commercial, annual) — <https://www.earthdefine.com/chm/>

## §AC-1 — Measured A/C access (the answer to "instead of estimating on income")

**Yes — real A/C data exists down to the census tract, and the definitive local source is the county assessor.**

Two practical replacements for the income proxy:

1. **County assessor "cooling type" parcel field — the authoritative local source.** Contra Costa, Los Angeles and Kern county assessors record heating/cooling system per parcel. A city deploying this tool *already owns* its assessor extract; joining the cooling field to parcels and aggregating to hexes gives measured A/C presence, not a model. Coverage is partial (not every record is populated), so pair it with #2 to fill gaps.

2. **Published tract-level A/C prevalence.** *A Comprehensive Dataset of Residential Air Conditioning Prevalence in the Continental United States* (Nature Scientific Data, 2025) classifies **central / other / evaporative / none** at **census-tract, ZIP and metro** resolution, built from ~103 M property records (Dewey/ZTRAX-type assessor data) with an XGBoost model. National coverage, so all four cities are included; join to hexes by tract.
   - <https://www.nature.com/articles/s41597-025-06104-3>

Caveats to keep even after switching: the tract dataset is itself **partly modelled** where assessor records are missing (in California only ~31 % of parcels had a recorded A/C type, so the rest is imputed), and evaporative coolers (common in Bakersfield) provide far less protection than refrigerated A/C — a "has cooling" flag should not be treated as "safe in a heat wave." But even a partly-modelled *measured* layer breaks the income circularity (AC-2) and is a real improvement over relabelling income.

Recommended approach: **assessor cooling field where available → tract prevalence to fill gaps → income only as a last-resort fallback, clearly labelled.** Also add an **evaporative-vs-refrigerated** distinction for the San Joaquin Valley cities.

Sources:
- Residential A/C prevalence dataset (Nature Sci Data 2025) — <https://www.nature.com/articles/s41597-025-06104-3>
- "Measuring A/C Access to Prepare Against Extreme Heat" (FAS) — <https://fas.org/publication/air-conditioning-data/>

---

## Recommended order of work

1. **C-1 / C-2 / C-3 — swap in USFS 2022 canopy.** Re-run `02c_canopy.py` against the new source for all four cities, re-score, re-derive `BRIEF.md`, redeploy. Changes every canopy number (for the better) and lets us drop the "ranks but doesn't certify" caveat.
2. **AC-1 / AC-2 — measured A/C.** Start with tract prevalence (fast, national); add assessor cooling fields per city where the city provides them.
3. **W-1 / W-2 — routed walk time on official cooling-centre locations.**
4. **D-1 — census-block dasymetric population.**
5. **C-4 / C-5 — canopy in UTM + nodata mask** (quick correctness fixes).

Items 1 and 2 change published figures, so they need a decision before they run — they are not silent refactors.
