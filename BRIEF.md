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
not a substitute for the professional assessment the CAP calls for — it measures canopy from a
satellite canopy-height model, not a tree inventory, and it deliberately produces no tree count.
It is offered as something to scope that assessment against, to cross-check a consultant's
results, or to attach to a grant application as evidence that the need is quantified. Every
figure is reproducible from public data and open source code.

---

## The finding

**Across San Ramon's 419 populated blocks, summer surface temperature tracks measured tree
canopy closely — `r = −0.64`, and −0.65 after removing a spatial trend — and the 25
highest-priority blocks average 3.6% canopy against a citywide median of 10.1% (about 11% over
the typical resident). Those 25 blocks hold 11,506 residents.**

Canopy here is measured from the Meta/WRI canopy-height model — ground under vegetation at
least 2 m tall — not from an NDVI greenness proxy, so an irrigated lawn does not count as
shade. The model reads roughly a third below professional aerial assessments (see Limitation 1),
so these percentages **rank** blocks against one another; they are not certified absolute
canopy figures.

The gap is closable with street trees alone. Those 25 blocks contain **33.6 km of residential
street frontage**; bringing them to the citywide median needs about **4,500 trees**, and the
public right-of-way could hold roughly **6,700** at 10 m spacing on both sides — so **in
aggregate the gap closes without private land.**

Block by block it is less tidy: **8 of the 25 need more trees than their own frontage holds**,
Carmelita S, Serena & Cordova NE and Capella worst among them at roughly 165–180 trees short
each. Those blocks need either planting on adjacent public land or an agreement with the
property owner. The other 17 fit entirely in the right-of-way.

At a nominal $500 per planted tree including three years of establishment care, that is about
**$2.24 million** spread over whatever period the City chooses — a capital line item, not a
bond measure.

### The ten thinnest blocks

| # | Area | Surface temp | Canopy | Residents | 65+ | Street frontage |
|---|---|---|---|---|---|---|
| 1 | Mosaic Park | 46.8 °C | 1.7% | 887 | 8.0% | 1,447 m |
| 2 | Valencia S | 46.9 °C | 3.2% | 925 | 8.6% | 1,279 m |
| 3 | Carmelita S | **51.1 °C** | **0.0%** | 178 | 10.6% | 493 m |
| 4 | Amador Lakes Apartments N | 47.7 °C | 7.3% | 210 | **47.6%** | 1,301 m |
| 5 | Carmelita | 49.3 °C | **0.0%** | 265 | 10.4% | 1,365 m |
| 6 | Valencia | 46.9 °C | 3.2% | 542 | 8.8% | 1,896 m |
| 7 | Seville | 47.0 °C | 2.7% | 525 | 8.1% | 1,619 m |
| 8 | Capella ⚠ | 49.3 °C | **0.0%** | 263 | 9.7% | 559 m |
| 9 | Fairway Village Apartments SE | 47.2 °C | 7.6% | 480 | 18.5% | 1,121 m |
| 10 | Valencia SW | 46.7 °C | 3.6% | 552 | 8.8% | 1,588 m |

A canopy reading of **0.0%** (Carmelita S, Carmelita and Capella above) means the height model
found no vegetation over 2 m across the block — consistent with a bare apartment-and-parking
block, but exactly the kind of value worth confirming on the ground. Eight of the top 25 read
under 1%, five of them at 0.0%.

⚠ **Capella (rank 8) is flagged, not asserted.** It runs 3.8 °C hotter than its neighbouring
blocks — above the 95th percentile of local anomalies citywide — carries 6.0 residents per
mapped building against a city median of 3.7, and now reads 0.0% canopy. That combination is
consistent with either a genuine hot spot or a mapping error. **It should be checked on the
ground before it is acted on.** Centre point: 37.78122, −121.92628.

## What this is *not*

**There is no income gradient in San Ramon's canopy, and this analysis does not claim one.**
Correlation between block median household income and measured canopy is **−0.19**, but that
falls to **−0.04 once a spatial trend is removed** — the raw tilt is *where* blocks sit, not
income. Mean canopy by income quartile is 13.6 / 13.9 / 11.7 / 7.5% — if anything the
**wealthiest** quartile is the least shaded, the opposite of the pattern seen countywide in
Contra Costa. The lowest-income quartile of this city has a median household income of
**$147,333**; this is a uniformly high-income city.

What remains is geographic: 6 of the 10 blocks above sit east of Dougherty Road, where mean
canopy is **6.5% against 13.3%** west of it. The newer Dougherty Valley subdivisions read green
on NDVI — they are irrigated — but carry markedly less mature tree canopy than the older west
side. Housing type and housing age were each tested against the ranking in the repository
write-up and neither explained it; the full figures are in `README.md` and `REDTEAM.md`.

## Sources

| Input | Source | Vintage |
|---|---|---|
| Surface temperature | USGS/NASA **Landsat 8/9** thermal (ST_B10), 9 scenes | summers 2022–2024 |
| Tree canopy | **Meta/WRI High-Resolution Canopy Height Map** (0.6 m) | 2009–2020 composite |
| Vegetation (context layer) | ESA **Sentinel-2** NDVI, 11 scenes, 20% cloud filter | summers 2022–2024 |
| Population, age, income | **US Census ACS** 2023 5-year, block groups | 2019–2023 |
| Buildings, streets, cooling sites | **OpenStreetMap** via Overpass | retrieved Aug 2026 |

Population is placed within block groups by residential floor area (dasymetric), not by area.
The city total reconciles to **85,569 against the ACS place total of 85,734 — 0.19%**.

## Three limitations, stated plainly

1. **Canopy is measured, but it ranks rather than certifies.** This uses a canopy-height model,
   not an NDVI proxy, so unlike an earlier version of this brief it does distinguish a shade
   tree from an irrigated lawn. But the model is a smooth modelled height surface, and it reads
   roughly a third below professional aerial canopy assessments — where a published aerial
   figure for Fresno is 14.6%, the same model reads about 9.1%. So a block's canopy **percentage
   here is a relative score, not an absolute coverage figure**, and there is deliberately no tree
   count: the model cannot resolve individual crowns reliably. Use it to rank and target, and let
   the City's own assessment set absolute numbers.
2. **Air conditioning is excluded from the score.** The underlying model estimates A/C access
   from income percentile. San Ramon's block-group medians run $100,906–$250,001 — uniformly
   high — so that transform would have invented a 35–95% spread across a city where it does
   not exist. The input is built and viewable but weighted zero. Every scored input is
   measured.
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
25 blocks, 11,506 residents, ~4,500 trees, 33.6 km of City right-of-way — and CS-1d has a
quantified need to put in a grant application.

Either outcome is useful to you. No software to adopt, no procurement, no commitment: one
cross-check against data the City already owns.

**Also worth knowing before you act on it:** one block in the top ten (Capella, rank 8) is
flagged above as possibly a data artifact, and should be looked at before it appears on any list.
