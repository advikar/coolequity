# CoolEquity — demo script (60–90s)

**Every number here is read off `data/la.geojson`, not off the spec.** Section 10 of
`../CoolEquity_BUILD_PROMPT.md` was written before the data existed and got two
claims wrong; see "What the spec got wrong" below so you don't say them on stage.

## Before you start

```bash
cd coolequity
python3 -m http.server 8000       # then open http://localhost:8000/app/
```

- Window at ~1440×860 or full screen. Below ~700px the 366px panel eats the map.
- Priority layer selected, cooling centers on, detail panel closed. That's the
  default state on a fresh load — just reload rather than clicking back to it.
- **No Wi-Fi?** Nothing to do. MapLibre is vendored and all data is local; the map
  loses only the CARTO street basemap and draws the county outline instead.
  Rehearse that look with `http://localhost:8000/app/?flat=1`.

---

## The script

**1 · Hook (10s)** — panel visible, don't touch anything yet.

> "Heat is the deadliest weather hazard on Earth — about 489,000 deaths a year —
> and it lands hardest on the poorest, least-shaded blocks. Cities have cooling
> budgets. What they don't have is a precise way to aim them."

**2 · Map (15s)** — Priority layer.

> "This is all of Los Angeles — 3,008 hexes, 6.5 million residents, 0.8 km²
> each. Every one scored on real satellite heat, real tree
> canopy, population, age, and walking distance to the nearest cooling centre.
> Nothing here is drawn by hand."

**3 · Story (20s)** — toggle **Redlining (HOLC)**, then **Cooling-access gap**.

> "These are the 1930s redlining grades. The D-graded blocks — the ones the
> federal government marked 'hazardous' and starved of loans — run **6.7 °C
> hotter** than the A-graded ones today, with **a third of the tree canopy**:
> 9% versus 26%. Ninety years later you can still read that policy off a
> thermal satellite."

Then the access layer:

> "And this is walking time to relief. Which cuts the other way — the redlined
> core is *close* to libraries and pools; it's the leafy suburbs that are far.
> So in LA, redlining shows up as heat and missing shade, not as distance."

**4 · Decision (25s)** — click the **#1 hex** in the ranked list (Westlake S),
then drag the canopy slider.

> "Number one in the city: Westlake. 47.4 °C surface temperature, **3% tree
> canopy**, 15,759 residents. Raise canopy here from 3% to 15% — about **2,470
> trees** — and you cool afternoons an estimated **0.36 °C** for all 15,759 of
> them, 1,797 of whom are over 65. Cost: roughly **$1.2 million**, or **$78 a
> resident**. That's the number a city council can actually vote on."

**5 · Close (10s)**

> "Every input except the redlining overlay is global — Landsat, Sentinel-2,
> population grids, OpenStreetMap. Point this at Lagos or Delhi tomorrow and it
> answers the same question: where does the first tree go?"

---

## What the spec got wrong

Section 10 of the build prompt makes two claims this dataset does not support.
Both were plausible; only one survived contact with the data.

| HOLC grade | hexes | mean LST | mean canopy | mean walk to relief | mean score |
|---|---|---|---|---|---|
| A | 136 | 38.7 °C | 26.0% | 20.3 min | 24.4 |
| B | 200 | 42.7 °C | 18.5% | 14.3 min | 38.4 |
| C | 450 | 45.1 °C | 12.2% | 13.2 min | 52.0 |
| D | 260 | 45.4 °C |  9.4% | 12.2 min | 54.1 |

1. **"D-graded areas run ~10 °C hotter" — overstated.** The real A→D gap is
   **+6.7 °C**. Still monotonic across all four grades, still a strong result.
   Quote 6.7.
2. **"…and are twice as far from relief" — backwards.** D areas are *closer* to
   cooling centres (12.2 min vs 20.3). They're dense inner-city blocks with
   libraries; A areas are low-density suburbs. Either drop the claim or reframe
   it as in beat 3 above. **Do not say it as written** — a judge with the access
   layer on screen can see it's false.

The 1,962 hexes outside the 1939 map are excluded from the table; they aren't a
fifth grade.

---

## Questions you should expect

**"Is the walk time routed?"** No — straight-line distance × 1.273, which is 4/π,
the exact expected Manhattan-to-Euclidean ratio over uniform bearings. It's the
right correction for a gridded city like LA. Say "estimated walking minutes";
never imply a street route.

**"Does shade actually cool, or is that just the coast?"** Across the 3,008
populated hexes, heat and greenness correlate at **r = −0.61**. It holds inside
every longitude band (−0.35 to −0.69), and partialling out a quadratic lon/lat
trend still leaves **−0.58**. It is not the coastal gradient.

**"Why the straight edge on the east side / why 6.5M not 10M?"** The bbox covers
the LA basin, not Antelope Valley. Known, deliberate, not a data failure.

**"Is A/C access measured?"** No — modeled from income and labelled `est.` in the
UI. It's the one input that isn't observed, and it carries 25% of the score.

**"What about the holes over the bay and Griffith Park?"** 478 hexes with
essentially no residents, dropped. They'd otherwise invert the headline
correlation (open ocean reads 18 °C with zero vegetation) and stretch the heat
ramp over a range no inhabited hex occupies.

**"How is this different from WRI's Cool Cities work?"** Same validated science —
we use their tree-cooling coefficient. The difference is what we do with it: a
per-hex ROI in dollars and residents, and a cooling-access framing, on a pipeline
that runs anywhere from satellite data alone.

---

## The 60s screen capture (do this, it's the last fallback)

Not yet recorded — this is a manual step. On macOS: **⌘⇧5 → Record Selected
Portion**, frame the browser window only, run the script above, save as
`demo.mp4` next to this file, and check it plays with Wi-Fi off. It's the
mitigation for the venue-network risk that vendoring MapLibre doesn't cover,
i.e. the laptop itself dying and someone else's machine having to present.
