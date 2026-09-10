# UX round 2 — layman feedback, September 9 2026

Feedback came from a first-time user of the live site. The pattern behind almost every
point is the same: the sidebar reads as a control surface built by the people who built
the model, not as a path a newcomer can follow. The words are the pipeline's words
("canopy-backed cells", "cooling-access gap", "mapped sites"), the sections sit in the order
they were coded, and nothing tells you what changed when you change something.

## Thoughts (how I approached it as a new person)

1. **One question per screen.** The landing page should answer "what is this and which
   city am I looking at?" with plain numbers. The sidebar should walk a newcomer through
   three decisions in order — *what matters* → *what to color the map by* → *where people
   can cool off* — and then hand them the ranked list. Everything else is one click deeper.
2. **Say what a thing is, not what the model calls it.** Every label gets a plain phrase;
   the precise term stays in the guide and the popover. "Cooling-access gap" becomes
   "Walking time to a cool place"; "Canopy deficit" becomes "Fewest trees".
3. **Never lose the user's work.** Weights and the chosen layer persist for the browser
   session, a reload stays on the map, and the home button goes back to the start screen
   without resetting anything.
4. **Show change.** When priorities change, each row says how far it moved and the list
   says how many of the top 25 are new. A silent re-sort is indistinguishable from nothing.
5. **Keep every number honest.** The walk-time complaint was a real data defect, not a
   wording problem (see item A below). Nothing in this round changes a score or a rank; the
   shipped weights put zero on walking time, so fixing it changes what is displayed, not
   who ranks where. The audit script confirms that per city.

## What the walk-time investigation found

Bakersfield cell 528 (Seven Oaks area) reads 254 min to a cooling site 1.1 km away. Cause:
the pedestrian graph was downloaded with osmnx's default `access!=private` filter, which
drops every street inside gated or private subdivisions. That cell has **no network nodes
inside it at all**, so its centroid snapped 524 m to a farm track that only reaches the
city by a 26 km loop; the two nearest sites snapped to a similar pocket path. Contra Costa
has the same defect (157 cells over 3× the straight-line distance, worst 19×); San Ramon is
milder (max 10.7×). Fix: include private-access streets (residents can walk out of their
own subdivision), snap each cell and each site to its several nearest nodes and take the
best door-to-door route, and flag any cell whose routed distance is still implausibly far
above the straight line. Graphs are re-downloaded to `walkgraph_<slug>_v2.graphml`.

## Todo (executed in this order, one at a time)

- [x] A1 `04b_routed_access.py`: private-access streets, k-nearest snapping, `access_src`,
      detour flag; `05_score.py` ships `access_src`. All three branches.
- [x] A2 Re-run 04b → 05 → 06 for Bakersfield, San Ramon, Contra Costa; confirm ranks
      unchanged; record before/after walk-time distributions in STATUS.
- [x] B1 Defaults & persistence: °F/mi default; session restore of weights, layer, mode,
      and "on the map" state; home button keeps weights; reload stays on the map.
- [x] B2 Start screen: city dropdown in the top corner (replaces the chip row and the
      "Compare local priorities" line); plain-language headline stats.
- [x] B3 Header: same city dropdown replaces "All cities"; bigger Simple / Explore switch.
- [x] B4 Sidebar hierarchy: numbered sections (1 What matters most · 2 Color the map by ·
      3 Places to cool off), walking-time overlay moved under Places to cool off, Priority
      areas collapsible, bigger and bolder section titles.
- [x] B5 Plain-language pass: presets, weights, layers, toggles, legend, list rows, detail
      panel, "How to use" steps, hover tooltip.
- [x] B6 Info buttons open a short popover (what it is, how to use it) with a "More in the
      guide" link, on hover, focus and click.
- [x] B7 Map reset button (zoom out, Priority layer, close selection, clear search).
- [x] B8 Ranking-change signals: per-row moved-up/down chips versus the default ranking and
      a "ranking updated" line; brief highlight when the list re-sorts.
- [x] B9 Guide: walking-access topic updated for the routing fix; "Using the map" topic
      updated for persistence, the popovers and the new layout; glossary of plain terms.
- [x] B10 Tests (`node tests/ui-contract.cjs`, unittest), browser check at desktop and
      mobile widths on all three cities, STATUS/HANDOFF, commit per branch, hand over the
      push + deploy command.

## Results (September 9, 2026)

Walking time, residential cells, before → after (ranks and scores unchanged everywhere):

| city | median | max | over 120 min | shorter by >5 min | longer by >5 min | detour-review | straight-line |
|---|---|---|---|---|---|---|---|
| Bakersfield | 68.2 → 61.4 min | 273 → 239 | 659 → 429 | 1,137 | 3 | 62 | 40 |
| San Ramon | 19.1 → 15.8 min | 52 → 46 | 0 → 0 | 65 | 1 | 0 | 0 |
| Contra Costa | 61.3 → 51.9 min | 352 → 268 | 660 → 457 | 1,234 | 11 | 34 | 20 |

The cell that prompted the report (Bakersfield 528, Seven Oaks) went from 254 to 18
minutes. The remaining flagged cells are either on the far-west edge where the mapped
network is a pocket of farm tracks (shipped as straight-line, labelled) or behind a
real barrier (routed value kept, labelled). The handful that got longer are
OpenStreetMap edits between the September 6 and 9 downloads, not the method.

Verification: `node tests/ui-contract.cjs` and the unittest suite pass on all three
branches; `06_audit_rebuild.py` reports max rank change 0 per city; browser checks at
desktop and 375 px on all three cities with no console errors.

Not done here, by design: Los Angeles (master) is still the legacy app and gets none
of this; the walking layer for LA remains the straight-line estimate.
