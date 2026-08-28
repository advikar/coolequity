# CoolEquity — San Ramon demo script (60–90s)

**Every number here is read off `data/sanramon.geojson` and was checked in the
running app, not off a spec.** This is the `san-ramon` branch; the Los Angeles
script is on `master` and its numbers do not transfer.

## Before you start

```bash
cd coolequity
python3 -m http.server 8000       # then open http://localhost:8000/app/
```

- Window at ~1440×860 or full screen. Below ~700px the 366px panel eats the map.
- You land on the **intro screen**; the map is already booted behind it, so the
  button is a fade, not a load. `?go=1` skips it.
- Priority layer, all four cooling-site categories on, weights at **Pipeline
  default**, detail panel closed. That is a fresh load — just reload rather than
  clicking back. The **home button** beside the wordmark returns you here.
- **No Wi-Fi?** Nothing to do. MapLibre and both typefaces are vendored and all
  data is local; you lose only the CARTO basemap. Rehearse with `?flat=1`.
- **There is no redlining layer and the panel says why.** Do not go looking for
  it — see beat 3.

---

## The script

**1 · Hook (10s)** — intro screen.

> "Heat is the deadliest weather hazard on Earth, and it lands hardest on the
> least-shaded blocks. Cities have cooling budgets. What they don't have is a
> precise way to aim them."

Then click **Explore San Ramon**.

**2 · Map (15s)**

> "This is all of San Ramon — every block inside the city limits, 540 hexes,
> 85,150 residents, about a tenth of a square kilometre each. Every one scored
> on real satellite heat, real tree canopy, population and age. Nothing here is
> drawn by hand. The darker it is, the more help it needs."

**3 · The suburb result (20s)** — this is the beat that makes San Ramon
interesting rather than a smaller Los Angeles.

> "San Ramon is a wealthy, leafy suburb — 21% canopy over the average resident.
> So you might expect this map to be flat. It isn't. Surface temperature runs
> from 39 to 51 degrees across four miles, and the top of the list is not a
> neighbourhood — it's **apartment complexes**. Fairway Village, Amador Lakes.
> Less shade, more people per hex, and in Amador Lakes' case **40% of residents
> over 65**. Heat inequity in a rich town looks like housing type, not income."

If asked about redlining: **San Ramon has no HOLC map, and the app says so
rather than showing an empty layer.** HOLC surveyed built-up cities in 1935–40;
San Ramon was farmland and didn't incorporate until 1983.

**4 · The model is not a black box (20s)** — click **Protect seniors**, then
**Pipeline default**.

> "The weights aren't buried in a config file. Ask a different question and the
> whole model recomputes across all 540 hexes, live. Ask 'who is most likely to
> *die* of this?' and the top spot moves from Fairway Village to **Amador
> Lakes**, where two in five residents are over 65."

Verified preset → #1 hex, if a judge wants to check:

| Preset | #1 |
|---|---|
| Pipeline default | Fairway Village Apartments SE |
| Heat first | Fairway Village Apartments SE |
| Shade gap | Fairway Village Apartments SE |
| Protect seniors | Amador Lakes Apartments N |
| No relief nearby | Canyon Oaks |
| Most people | Canyon Oaks |

Then click any hex:

> "And for any block, here's the arithmetic — what we measured, where it sits on
> the city's scale, times the weight, equals points."

**5 · Decision (25s)** — click the **#1 hex** (Fairway Village Apartments SE),
drag the canopy slider to **25%**.

> "Number one: Fairway Village. 47.2 °C surface temperature, **16% canopy**, 451
> residents, 106 of them over 65. Raise canopy here to 25% and you cool
> afternoons an estimated **0.28 °C** for all of them. Cost: about **$129,000**,
> or **$286 a resident**. That's a number a city council can actually vote on —
> and for a town this size it's a line item, not a bond measure."

**6 · Close (10s)**

> "Every input here is global — Landsat, Sentinel-2, OpenStreetMap, a census.
> This started as Los Angeles, three thousand hexes and six and a half million
> people. Re-pointing it at a town of eighty-five thousand was a config change.
> Point it at Lagos or Delhi tomorrow and it answers the same question: where
> does the first tree go?"

---

## Questions you should expect

**"Is this real data?"** Yes, all of it, and the honest caveats are labelled in
the UI. Landsat 8/9 thermal and Sentinel-2 NDVI composited over the summers of
2022–2024 from Microsoft's Planetary Computer. ACS 2023 five-year for Contra
Costa County. City limits from Census TIGERweb. Cooling sites and neighbourhood
names from OpenStreetMap. Nothing is synthetic and nothing is copied from the LA
build.

**"Why three summers, when the LA build used one?"** Because San Ramon is small.
Summer 2023 alone yields **one** Landsat scene under the 20% cloud filter, and
one scene is an afternoon, not a median. Three summers gives 9 Landsat and 11
Sentinel-2 scenes at the *same* strict cloud threshold — more data, not looser
data. The alternative was raising the cloud limit, which buys quantity with
quality, and that's the wrong trade for a thermal median.

**"Is A/C access in the score?"** **No, and that's deliberate — this is the good
question to get.** A/C isn't measured by any census; it's modelled from income
percentile. In LA that works because block-group medians span $20k to $250k. San
Ramon's span **$102k to $250k** — so the same transform would manufacture a
35%-to-95% spread of "A/C access" across a town where essentially everyone can
afford it, and then hand that invented variation a quarter of the score. So it's
built, viewable on the map, and **weighted zero**. Every input the score actually
uses is measured.

**"Isn't a hex smaller than a census block group?"** Yes — about a ninth, at this
resolution. Heat and canopy are genuinely per-hex (30 m satellite rasters).
Population, age and income are real ACS numbers spread by area, so they vary
smoothly across neighbours rather than block by block. That's stated in the app's
footer. The alternative was res 8, which is 71 hexes for the whole city and
doesn't look like a map.

**"Does shade actually cool, or is that just terrain?"** Across the 540 populated
hexes, heat and greenness correlate at **r = −0.797**. That's stronger than the
LA build's −0.61, and unlike LA there's no coastline here to confound it.

**"Is the walk time routed?"** No — straight-line × 1.273 (= 4/π, the exact
expected Manhattan-to-Euclidean ratio over uniform bearings) at 4.8 km/h. Say
"estimated walking minutes"; never imply a street route.

**"What counts as a cooling site?"** 25 of them from OpenStreetMap: 12 community
centres, 5 public pools, 5 senior centres/shelters, 3 libraries. Places a
resident with no A/C could walk to and sit in the cool for free — **not** a list
San Ramon has formally designated for a heat emergency.

**"Where does the $500 a tree come from?"** A planning assumption, and the panel
says so in those words — the order of magnitude US municipal programmes budget
for a planted street tree plus about three years of establishment care. Not a
quote. The cooling coefficient is WRI's published figure and 40 m² of crown per
mature tree is a standard planning number. **Don't defend the $500 as a
measurement**; the defensible claim is dollars per resident cooled, which makes
two neighbourhoods comparable whatever unit cost you plug in.

**"Your scale is relative — what if the city just isn't hot?"** Correct, and the
legend concedes it: every input is min–max normalised *within the city*, so 100
means first in line here, not hot in absolute terms. That's the deliberate trade
for portability. Switch to the **Surface temperature** layer for absolute values —
and note San Ramon's max is 51.1 °C surface, which is not nothing.

**"Can I look at my city?"** Not today, and the picker says so rather than
loading San Ramon's numbers under another name. Los Angeles is in the list
without a data flag because it's built on `master`, not on this branch.

---

## The 60s screen capture (do this, it's the last fallback)

Not yet recorded. On macOS: **⌘⇧5 → Record Selected Portion**, frame the browser
window only, run the script above, save as `demo.mp4` next to this file, and
check it plays with Wi-Fi off.
