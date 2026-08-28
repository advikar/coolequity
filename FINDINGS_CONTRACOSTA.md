# Contra Costa County build — what it found, and why it is not shippable yet

**Status: the equity finding is strong and real. The heat finding does not reproduce,
and the score is 35% heat. Do not present this as a heat map.**

Built 28 Aug 2026 from the same pipeline as San Ramon: H3 res 8, 2,695 populated hexes,
1,161,570 residents reconciling to the ACS county total of 1,161,458 (**0.01%**).

---

## 1. The equity gradient is real — this is what San Ramon could not show

| Income quartile | Median income | Mean canopy | Population |
|---|---|---|---|
| Poorest 25% | $93,125 | **14.8%** | 465,728 |
| 2nd | $138,132 | 19.8% | 327,283 |
| 3rd | $164,920 | 20.7% | 84,068 |
| Richest 25% | $230,581 | **28.3%** | 283,729 |

- `corr(income, canopy) = **+0.422**` county-wide, **+0.630** in the Richmond/El Cerrito
  west. San Ramon's was −0.037.
- Poorest vs richest quartile: a **13.5-point canopy gap, t = −25.3**.
- **All 25 top-priority hexes fall in the poorest income quartile.** Top-25 median income
  $74,563 against a county median of $158,608.
- Top of the list is Richmond (Triangle Court, Atchison Village, Barrett Terrace) and
  Concord's Monument corridor — which is where anyone who knows the county would look.

**Caveat, and it is a real one:** detrending for a quadratic spatial surface drops
`corr(income, canopy)` from +0.422 to **+0.189**. A substantial part of the raw gap is
*where* rich and poor areas sit — the wooded Lamorinda hills versus the Richmond shoreline —
rather than differential investment in comparable terrain. **Quote +0.42 with the detrended
+0.19 beside it**, or the first hydrologist in the room will do it for you.

## 2. The heat finding does not reproduce, and that breaks the score

San Ramon: `corr(LST, canopy) = −0.800`, and −0.808 detrended. Rock solid.
Contra Costa: **−0.120**, and −0.149 detrended.

It is not hiding in a sub-region. Tested every way:

| Area | n | LST~canopy | detrended |
|---|---|---|---|
| Whole county | 2,689 | −0.120 | −0.149 |
| West of −121.90 (urban core) | 1,448 | −0.018 | −0.200 |
| Richmond / El Cerrito only | 1,019 | **+0.043** | −0.130 |
| Central (Concord / Walnut Creek) | 723 | −0.084 | −0.326 |
| East (Antioch / Brentwood / Delta) | 518 | −0.090 | **+0.221** |

By longitude band it swings from **+0.381 to −0.092**. There is no consistent shade effect
at this scale.

**Why, most likely.** The county spans a marine-to-inland climate gradient — mean LST is
36.8 °C in the west and 43.1 °C in the east, and **38.8% of all LST variance is explained by
longitude and latitude alone**. Richmond is cool *and* bare; Brentwood is hot *and* irrigated
farmland. Absolute surface temperature across this county is mostly a map of distance from
the Bay. Resolution may contribute too — res 8 hexes (0.77 km²) mix houses, streets, parks and
parking — but LA managed −0.61 at res 8, so climate heterogeneity is the better explanation.

**Why this is not a footnote:** `WEIGHTS["heat"] = 0.35`. The single heaviest input in the
score is the one whose relationship to everything else has collapsed. Min-max normalising LST
across the whole county also means Richmond's 41 °C and Antioch's 52 °C are ranked on one
scale, as if a Richmond resident experiences 41 °C the way an Antioch resident experiences 41 °C.
They do not.

## 3. Dasymetric population placement was refused, automatically

The San Ramon method — placing residents by OSM building floor area — **must not be used
here**, and `03_census.py` now detects that itself rather than relying on someone noticing:

```
mask check: 139,121 mapped buildings vs 426,585 ACS housing units = 0.33 coverage
!! DASYMETRIC REFUSED: coverage 0.33 < 0.50 — the mask is a sample, not a census
!! falling back to AREA weighting
```

The completeness problem is bad; the bias is worse. OSM coverage by income quartile runs
**0.07 / 0.07 / 0.08 / 0.33** — volunteers have mapped the richest quartile **4.7× better**
than the poorest. Since population multiplies the priority score, weighting by that mask would
have moved residents out of poor neighbourhoods and demoted them. An equity tool that
under-ranks poverty because Blackhawk is better mapped than North Richmond is worse than no
tool. The guard and its thresholds are in `config.DASY_MIN_COVERAGE` /
`DASY_MAX_INCOME_BIAS`. **Do not raise them to force dasymetric back on — fix the mask.**

## 4. A bug this build found in the shared pipeline

`02_satellite.py` sorted candidate scenes by cloud cover globally and kept the best
`MAX_SCENES = 30`. For a single-tile city that is fine. Across a county spanning several
Sentinel-2 MGRS tiles it took nearly all 30 from the clearest tile, and **NDVI came back 37%
valid with 1,723 of 2,859 hexes empty**. Fixed by budgeting scenes per tile: now 101 scenes
across 4 tiles, **100% valid**. This bug was invisible at city scale and would have silently
corrupted any large-area build.

## 5. What to do next

Three honest options, in the order I would try them:

1. **Reframe as a canopy-equity map and drop or heavily downweight heat.** The defensible
   claim here is "the poorest quarter of this county has half the tree cover of the richest",
   which needs no thermal data at all. This is a one-line weights change plus copy.
2. **Re-scope to one climate zone.** Not simply "the west" — that did not work either. It
   would mean a genuine climate-zone segmentation, and normalising heat *within* zone.
3. **Keep the county as a scale demonstration only** and lead publicly with San Ramon, where
   the mechanism holds.

**Not recommended:** shipping this as-is with a 35% heat weight and a heat legend. The map
would look convincing and the top of the list would be defensible for the wrong reason —
Richmond ranks first on low canopy and low income, not on being hot.
