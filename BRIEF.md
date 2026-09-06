# A first-pass canopy assessment for CAP Measure CS-1b

**Where San Ramon's tree canopy is thinnest, block by block — and what closing the gap
would cost**

Prepared by *[your name]*, an independent student project · Data current as of September 2026
Method, source code and every figure below: `github.com/advikar/coolequity` (`san-ramon` branch)
Interactive map: `advikar.github.io/coolequity/sanramon/app/`

> This is an outside analysis offered for cross-checking. It is not a City product and has
> not been reviewed by the City. Where it is uncertain, it says so.

---

## Why this is addressed to you

San Ramon's **Draft Climate Action Plan (April 10, 2025), Measure CS-1**, commits the City to
work this analysis was independently built to do:

- **CS-1b** — *"Conduct a Tree Canopy assessment … including **identifying areas with below
  average canopy coverage**"*, and set *"a goal of having **no significant difference in canopy
  coverage between census blocks** in the community."*
- **CS-1c** — *"prioritize tree implementation in **areas with populations most at risk to
  extreme heat impacts** (e.g., older adults …)."*
- **CS-1d** — a Tree Trust for *"selected communities with below average tree canopy coverage"*,
  plus USDA / California ReLeaf / Urban and Community Forestry grant applications.
- **CS-1e** — *"an **interactive map** showing the results of the tree canopy assessment along
  with areas identified for new tree canopy."*

**This document is a free first pass at CS-1b and CS-1c, with a working interactive map.** It is
not a substitute for the professional assessment the CAP calls for — it measures canopy from aerial imagery, not a tree inventory, and it deliberately produces no tree count.
It is offered as something to scope that assessment against, to cross-check a consultant's
results, or to attach to a grant application as evidence that the need is quantified. Every
figure is reproducible from public data and open source code.

---

## The finding

**San Ramon's canopy problem is not its total — it is the distribution.** Over the average
resident the city carries **17.7% tree canopy** (block median 16.6%), slightly *above* the
California urban average of 14.5%. But that average hides a steep spread: **36% of residents —
about 31,000 people — live on blocks under 15% canopy, and the 25 thinnest blocks average
8.3%, several reading essentially zero.** Summer surface temperature tracks canopy across the
city at `r = −0.60`. Those 25 blocks hold 9,420 residents.

This is precisely what CS-1b targets: not "plant more trees everywhere," but *"no significant
difference in canopy coverage between blocks."* Today that difference is large.

Canopy here is the **USFS / CAL FIRE 2022 California Urban Tree Canopy** — an aerial
classification from 0.6 m 2022 NAIP imagery, not an NDVI greenness proxy, so an irrigated lawn
does not count as shade and the percentages are citable in absolute terms, not just as a
ranking. (An earlier version of this brief used a satellite canopy-height model that read
~35% low; the figures here are the corrected, aerial-grade numbers.)

The gap is closable with street trees alone. Those 25 blocks contain **29.7 km of residential
street frontage**; bringing them to the citywide median needs about **5,700 trees**, and the
public right-of-way could hold roughly **5,900** at 10 m spacing on both sides — so **in
aggregate the gap closes almost entirely without private land.**

Block by block it is less tidy: **10 of the 25 need more trees than their own frontage holds.**
Those blocks need either planting on adjacent public land or an agreement with the property
owner; the other 15 fit entirely in the right-of-way.

At a nominal $500 per planted tree including three years of establishment care, that is about
**$2.85 million** spread over whatever period the City chooses — a capital line item, not a
bond measure.

### The ten thinnest blocks

| # | Area | Surface temp | Canopy | Residents | 65+ | Street frontage |
|---|---|---|---|---|---|---|
| 1 | Carmelita S | **51.1 °C** | 0.1% | 178 | 11% | 493 m |
| 2 | Carmelita | 49.3 °C | 0.4% | 265 | 10% | 1,365 m |
| 3 | Valencia S | 46.9 °C | 7.9% | 925 | 9% | 1,279 m |
| 4 | Capella ⚠ | 49.3 °C | 0.8% | 263 | 10% | 559 m |
| 5 | Amador Lakes Apartments N | 47.7 °C | 10.4% | 210 | **48%** | 1,301 m |
| 6 | Serena & Cordova | 48.6 °C | 0.2% | 261 | 12% | 1,280 m |
| 7 | The Preserve | 49.2 °C | **0.0%** | 153 | 19% | 1,109 m |
| 8 | Serena & Cordova NW | 50.5 °C | 0.2% | 114 | 11% | 1,310 m |
| 9 | The Preserve NE | 47.3 °C | 4.8% | 430 | 8% | 1,241 m |
| 10 | The Vintner W | 48.5 °C | 7.8% | 245 | 20% | 1,088 m |

A canopy reading near **0.0%** (The Preserve, Serena & Cordova, Carmelita S above) means the
aerial classifier found essentially no tree cover across the block — consistent with a bare
apartment-and-parking block, but worth confirming on the ground. Seven of the top 25 read
under 1%.

⚠ **Capella (rank 4) is flagged, not asserted.** It runs 3.8 °C hotter than its neighbouring
blocks — above the 95th percentile of local anomalies citywide — carries 6.0 residents per
mapped building against a city median of 3.7, and now reads 0.0% canopy. That combination is
consistent with either a genuine hot spot or a mapping error. **It should be checked on the
ground before it is acted on.** Centre point: 37.78122, −121.92628.

## What this is *not*

**There is no income gradient in San Ramon's canopy, and this analysis does not claim one.**
Correlation between block median household income and measured canopy is **−0.18**, and falls
to **−0.09 once a spatial trend is removed** — and it runs the "wrong" way: mean canopy by
income quartile is 19.3 / 18.4 / 16.8 / 14.0%, so if anything the **wealthiest** quartile is
the *least* shaded — the opposite of the pattern seen countywide in Contra Costa. The
lowest-income quartile of this city still has a median household income of **$163,938**; this
is a uniformly high-income city, and the canopy gap here is not an income story.

What it is instead is a **building-type story**: the thinnest blocks are apartment-and-parking
complexes and a few dense townhome pockets in central and western San Ramon (Carmelita, The
Preserve, Serena & Cordova), where mature street trees were never established. The eastern
Dougherty Valley subdivisions run a little lower than the west on average (13.2% vs 17.6%) —
irrigated and green on NDVI, but younger and less shaded — yet they hold none of the ten
thinnest blocks. Target the bare complexes first.

## Sources

| Input | Source | Vintage |
|---|---|---|
| Surface temperature | USGS/NASA **Landsat 8/9** thermal (ST_B10), 9 scenes | summers 2022–2024 |
| Tree canopy | **USFS / CAL FIRE California Urban Tree Canopy** (0.6 m NAIP, aerial classification) | 2022 |
| Vegetation (context layer) | ESA **Sentinel-2** NDVI, 11 scenes, 20% cloud filter | summers 2022–2024 |
| Population, age, income | **US Census ACS** 2023 5-year, block groups | 2019–2023 |
| Buildings, streets, cooling sites | **OpenStreetMap** via Overpass | retrieved Aug 2026 |

Population is placed within block groups by residential floor area (dasymetric), not by area.
The city total reconciles to **85,569 against the ACS place total of 85,734 — 0.19%**.

## Three limitations, stated plainly

1. **Canopy is measured from aerial imagery, but it is extent, not a tree inventory.** This uses
   the USFS/CAL FIRE 2022 canopy layer — a 0.6 m aerial classification, not an NDVI greenness
   proxy and not a satellite height model — so the percentages are defensible as absolute
   coverage, not merely a ranking. What it does **not** provide is a tree count or species: it
   maps canopy *area*, so CS-1b's inventory component still needs a ground or LiDAR survey.
   There is deliberately no tree count in this tool — aerial canopy cannot resolve individual
   crowns reliably — so treat the per-block tree figures as planting *capacity*, not a census.
2. **Air conditioning is excluded from the score (a choice, not a data gap).** A/C access is now
   *measured* — US Census LACE (2023) tract estimates, 66–100% across San Ramon — and is shown
   as a layer. It is weighted zero in the score here because this is a near-universally
   air-conditioned city and the actionable levers are canopy, heat and age; the City can enable
   it if it prefers. Every scored input is measured.
3. **Resolution and thermal sampling.** Blocks are ~0.11 km²; ACS block groups are about nine
   times larger, so **age and income vary smoothly between neighbouring blocks** and should
   not be read at single-block precision. Surface temperature is a median of 9 Landsat scenes
   across three summers, not a continuous record. And surface temperature is not air
   temperature and not indoor temperature — with near-universal A/C here, it is a measure of
   outdoor thermal environment, not of health risk.

**No San Ramon-specific heat health data was found.** California publishes heat-illness
emergency department rates at **county** level (Tracking California); ZIP-level records exist
within HCAI but require a Limited Data Request. County figures are not presented here because
they are not San Ramon figures.

## One ask

**Cross-reference these 25 blocks against whatever street tree records the City already holds.**

If those records show these streets are already well planted, then the height model is missing
canopy it should see and the ranking needs adjusting where it disagrees with your inventory —
worth finding out cheaply.

If they show these streets are *not* planted, then CS-1b has a ranked, costed starting list —
25 blocks, 9,420 residents, ~5,700 trees, 29.7 km of City right-of-way — and CS-1d has a
quantified need to put in a grant application.

Either outcome is useful to you. No software to adopt, no procurement, no commitment: one
cross-check against data the City already owns.

**Also worth knowing before you act on it:** one block in the top ten (Capella, rank 4) is
flagged above as possibly a data artifact, and should be looked at before it appears on any list.
