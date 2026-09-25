# CoolEquity: live-site outreach audit

Audited September 24–25, 2026 Pacific; continued September 25 at the owner's request.

**Verdict: hold broad, unaccompanied outreach until the boundary inconsistency, mobile homepage and partial-save bug are fixed, and the prominent claims below are corrected.** A guided conversation explicitly asking for feedback on an exploratory prototype is reasonable today. This is not a verdict that the whole model is wrong: the default ranking arithmetic and current automated contracts pass.

Live release: `8ec3539574f036e8563e3713582b2723733abe3d`. The deployed source is the adjacent `coolequity-app` repository, not this older per-city-branch checkout. This audit changed no product code, pipeline, dataset or city branch, and deployed nothing. It added this report, an evidence manifest and a STATUS entry here. All five study areas were inspected.

## Verification and limits

- Downloaded 56 public assets successfully: chooser plus each study area's app, guide, directory, settings, registry, guide assets and four GeoJSON files. All 55 city assets match local source, allowing for the build's analytics injection. The chooser's remaining difference is its injected analytics/privacy/release content.
- Ran `PYTHONDONTWRITEBYTECODE=1 bash scripts/test.sh` in the deployed-source repository. All **8,435 residential default ranks**, **43,440 scenario cases**, **45 Python tests**, generated column dictionaries and the complete site build passed.
- Opened and verified populated lists on all five live maps. Tested county detail; Pittsburg search, selection, cost change, reset warning and keyboard focus wrap; and methods-guide search. The cost-only reset warning now works, and Tab from its last button returned to Stay.
- Inspected desktop screenshots and actual **390×844** phone emulation. The county list and detail are usable at that width. The homepage has a reproducible layout regression. This was not a physical-phone, Safari or screen-reader certification pass.
- Generated and read a live Bakersfield briefing with one pre-existing shortlisted area. Print-preview automation stalled; **final PDF pagination remains unverified**. No clipping defect in the final PDF is asserted. The report tab was closed after the attempt.
- Independently checked boundary intersections and street lengths using the shipped geometry and cached street source. Executed the actual partial-save functions in an isolated JavaScript context to reproduce the save bug.
- Continued the handoff audit: reproduced missing default shortlist planting fields using the actual shared exporter/scenario functions and county data. Generated a second, county briefing with no shortlist; its HTML table fits the 704px content width. Confirmed the fixed light-mode explanation uses RGB(138,75,0) on RGB(246,248,250), approximately 6.4:1 contrast. Neither an HTML-width check nor a color sample substitutes for full PDF/accessibility verification.
- Checked primary Census, county, Concord, San Francisco and analytics-provider documentation. This was not a complete rebuild from raw imagery, an independent canopy ground-truth study, a facility-hours verification, a penetration test, or a complete audit of every external source link. Pre-existing shortlists and field notes were not changed; test cost and theme edits were restored.

## Fix before broad outreach

### 1. P1 — Population, jurisdiction and planting capacity use different geographic footprints

**Confirmed data/implementation defect, shared pipeline; demonstrated in Contra Costa, Bakersfield and San Ramon.**

`01_make_grid.py` retains whole hexagons that intersect the study boundary. `03_census.py:270` clips census intersections to that boundary. However, `04_overlays.py:462` counts streets against whole hexagons, and `04d_jurisdiction.py` labels their whole-cell centroids. Consequently the app can combine residents inside one jurisdiction with streets and a city label outside it.

Examples from current data; street remeasurement uses California Albers and differs slightly from the pipeline's projection/rounding:

| Build / area | Displayed jurisdiction | Rank | Cell inside study boundary | Counted street length outside boundary |
|---|---|---:|---:|---:|
| Contra Costa #517, Piedmont Pines | Oakland | 2,284 | 19.47% | approximately 100%; published 9,770 m |
| Contra Costa #2174, Wallis Ranch | Dublin | 1,444 | 47.24% | approximately 100%; published 4,880 m |
| Contra Costa #834, Albany Hill Park | Albany | 126 | 39.44% | 42.9%; published 6,321 m |
| Bakersfield #1515, Bakersfield E 45 | East Bakersfield | 73 | 44.35% | 52.3%; published 1,848 m |
| San Ramon #192, Amador Lakes Apartments | Dublin | 102 | 31.00% | 63.2%; published 840 m |

The county's live city filter includes Oakland (10 cells), Berkeley (2), Albany (4) and Dublin (3). San Ramon's filter includes Danville and Dublin. Ranked whole-cell centroids outside the study boundary occur in all five datasets: county 108; Bakersfield 433; San Ramon 27; West Contra Costa 19; Pittsburg/Bay Point 49. This **does not mean those populations are outside the study area**: population was clipped. It identifies mixed geographic support and misleading attribution.

**Fix:** define a study-area footprint per cell and use it consistently for jurisdiction assignment, street length, scenario land area and environmental aggregation, or clearly separate whole-cell context from in-boundary calculations. Assign jurisdiction using the in-boundary portion; do not silently drop residents in edge cells. Rebuild affected outputs and sensitivity results as necessary.

**Acceptance:** county #517/#2174 cannot offer out-of-county street capacity as a county planting scenario; all five builds have explicit boundary-consistent quantities; totals reconcile and all-city tests still pass. Test jurisdiction filters against edge cells, not only interior cells.

### 2. P1 — Mobile homepage squeezes the main content into half the screen

**Confirmed visually on live homepage at 390×844.**

The study-area selector occupies the left portion while the wordmark, headline, description and statistics stack in a narrow right column. The main action falls below the first screen. The selector itself truncates the study-area name. Document width is correctly 390px, so a horizontal-overflow test would miss this.

Cause: `site/index.html:29` makes `.hero` a row flex container. The mobile rule around line 65 moves `.hero .pick` into normal flow but does not stack it above `.hero-in`.

**Fix:** a single-column mobile hero with the selector above the introduction; full-width content and a readily visible primary action. Check 360, 390 and 430px, long study-area names and increased text size. The map's mobile List default and detail layout are substantially better and should be retained.

### 3. P2 — Saving one area incorrectly marks other edited areas as saved

**Confirmed in isolated execution of the actual shared functions.**

`app/index.html:1686`, `exportCell('json')`, writes only the selected area's record, then calls global `markSaved()`. `scenarioSig()` includes every user-edited planting share. Reproduction: edit A to 40% and B to 80%; save A. `isDirty()` changes from true to false, although the file contains only A at 40% and no record of B. Reset/leave can then discard B without the intended warning.

**Fix:** only mark the state actually exported as saved, or have a scenario save include all edited shares. Keep single-area export and whole-scenario save distinct. Add a meaningful regression test for two edited areas followed by a one-area save and reset/reload.

**Acceptance:** B remains protected until a file containing B has been saved. The existing cost-only warning must keep working.

### 4. P2 — “2.0M residents” double-counts overlapping study areas

**Confirmed homepage claim and dataset arithmetic.**

Summing all five ranked datasets yields **2,022,012**, but San Ramon, West Contra Costa and Pittsburg/Bay Point are detail views within Contra Costa County. County plus Bakersfield contains **1,575,367 allocated residents** in the current ranked data. The three extra views add 446,645 duplicate study-view residents, not new geographic reach.

**Fix:** use “About 1.6M residents across covered regions” with a clear definition, or remove the combined resident KPI. Label 8,435 as “ranked cells across five overlapping study views”; it is a valid sum of records, not 8,435 non-overlapping neighborhoods. Do not replace this with a claim of precisely counted unique people: these are allocated ACS estimates.

### 5. P2 — Prominent cooling labels overstate facility verification

**Confirmed live text; limits exist but are less prominent.**

The county start screen says **“486 places to cool off.”** Lists say “walk,” detail says “Walk to cooling,” and the preset says “Far from cooling.” These are broader OpenStreetMap discovery sites, not 486 verified, accessible, open cooling centers. The separate county directory contains 17 listed locations. The guide explains the difference well, but users see the stronger labels first.

Routing also permits private-access streets and uses straight-line connections to multiple nearby network nodes. This is an estimated network-access screen, not a verified public or accessible walking route. Current county data has 21 residential straight-line fallbacks and 2,238 approach-review flags; this is not a minor exceptional caveat.

**Fix:** “Mapped facilities — status unverified”; “Estimated walk to a mapped facility”; clearly separated county-listed locations. Put the qualification next to the first number. Retain “call before visiting” on the official directory. The [county heat resources](https://www.contracosta.ca.gov/10174/Heat-Safety-Tips-Places-to-Cool) should remain the route to official information.

### 6. P2 — Headline promises benefit optimization; the model ranks relative need

**Interpretation/product-positioning issue, not arithmetic failure.**

“Where would new trees help residents most?”, “Put tree investment where it matters most,” and the briefing's similar title imply comparative intervention benefits. The model combines project-chosen need indicators. It does not establish which feasible planting produces the greatest health benefit, pedestrian shade or value per dollar. County heat is deliberately weighted zero; walking time is zero by default in every build. The chooser lede still sounds as though every listed input is scored everywhere.

**Fix:** “Find areas to investigate for new shade trees.” Follow with “Compare tree cover, heat and population data, then explore a planting scenario.” Use “Default priorities” instead of “Recommended mix,” and “Rank sensitivity range” instead of “Likely rank.” Show which inputs actually influence each build. These are short wording changes that align the first impression with the existing disclosures.

## Correct before sharing briefings or relying on the methods guide

### 7. P2 — Briefing loses per-area qualifications and has ambiguous map scope

The live Bakersfield briefing presents #12, Crestview Meadows SW 45, as **0% trees** without the map list's **65% assessed / partial** badge. Its existing shortlisted height-model area displays 8% tree cover without a per-area source label. A source inventory at the end cannot tell a reader which row is partial or modeled. Proxy values can also appear in the top-table “Trees” column as `/100`, despite being a different kind of measurement.

`openReport()` uses the full `LIVE.order` top 25 while taking an image of the current viewport/layer/filter. A filtered or zoomed map can therefore illustrate a different scope from the table without a clear caption. Final PDF pagination is still unverified, including the potentially wide 11-column table.

**Fix:** carry source/coverage flags into each row; separate percent cover from greenness index; state table scope and map scope explicitly. Inspect actual Letter PDFs with 0, 1 and 6 shortlisted areas, long notes, a partial/proxy cell, custom priorities and an active city filter. Do not treat readable HTML as proof of printable output.

### 8. P2 — Guide has current/historical and formula inconsistencies

Examples in the live county guide:

- Walking-access technical text says 488 sites, later says 486; it describes 21 fallbacks, then says all 2,859 overlay cells are routed. The current residential data has 2,676 routed plus 21 straight-line cells. Put old audit facts in a clearly dated historical note and use current counts in the method.
- The population-weight explanation says population is normalized between the second and 98th percentiles. `05_score.py:67` actually uses the minimum and 98th percentile for population. Risk inputs use second percentile to maximum; protective inputs use minimum to 98th percentile. Some report prose still summarizes this too loosely.
- City intro copy says the average tree-cover statistic uses areas with an aerial assessment, but `updateIntro()` includes all `green_src==='canopy'` cells, including height-model and lidar sources. In the county, 1,330 ranked cells use the height model and 126 use lidar. This is a materially mixed source pool.
- “Methods reviewed September 7” and “current release September 22” no longer describe the September 24 code release precisely. Distinguish source vintage, method update and software release. Use “project methods updated” if there was no independent review.

**Fix:** generate current counts and source summaries from data; share formula descriptions; preserve historical results separately. The generated export column dictionary now passes its synchronization check, which is a good pattern to extend.

### 9. P2 — Sensitivity method still needs a narrower interpretation and allocation review

The previous double-smoothing bug is fixed: `05b_stability.py` now starts from raw census age share and smooths once, with an explicit check against the published share. That improvement is real.

However, `overlap_shares()` still uses whole-cell geometric overlap to average source-area perturbation factors. The point pipeline clips to study boundaries, can use residential-building allocation, and uses occupied homes for A/C aggregation. These are not the same contribution weights. The sensitivity run also holds heat, tree cover and allocation uncertainty fixed. I have **not quantified the rank-band effect** of this remaining approximation, and it does not establish wrong point ranks.

**Fix:** either propagate the same source contributions as the point model or explicitly document the overlap-weighted approximation. Keep the range framed as a limited sensitivity experiment. Obtain a spatial/statistical methods review before claiming comprehensive uncertainty or using “Stable top tier” as a robust investment recommendation. Census itself describes [LACE as an experimental modeled product](https://www.census.gov/data/experimental-data-products/lace.html); the current A/C guide correctly says this.

### 10. P2 — Homepage privacy statement is too absolute

The live chooser again says “no personal data.” The build injects that sentence in `scripts/build_site.py`, despite the earlier audit recording a more precise replacement. [GoatCounter's policy](https://www.goatcounter.com/help/privacy) describes aggregate browser/system/location information and temporary in-memory IP/user-agent processing. Account-specific collection settings were not inspected.

**Fix:** say that cookieless page-view analytics are used, link the provider policy, and state accurately that notes and shortlists remain in the browser unless exported. Avoid an absolute claim about all data processing. This is a disclosure correction; no upload of notes was observed or alleged.

## Improvements that would make expert review easier

### 11. P3 — Cost presets compare different scopes, and the low price anchors the result

The arithmetic and current cost/survival labels are sound. County #641 shows 513 planted, 359 surviving at 70%, and $256,500 at $500/tree. But $500 excludes establishment care while $2,000 and $3,500 represent broader program assumptions. They are not low/base/high bids for one identical service.

[San Francisco's primary source](https://sfpublicworks.org/3500treesproject) supports $12M for 3,500 trees with site work, workforce development and three-year watering. [Concord's page](https://www.cityofconcord.org/1289/USDA-Forest-Service-Grant) describes planting plus education, training and a management plan; dividing a program budget by trees does not establish a transferable installation price or a specific one-year watering package.

**Improve:** name presets by scope, prominently say “planting only” beside the default total, and offer an editable scope note for custom prices. Ask reviewers for local costs and establishment requirements. Retain 70% survival and 40 m² crowns as explicit assumptions, not measurements.

### 12. P3 — Reduce friction and terminology before asking busy reviewers to explore alone

- The main entry path has two successive Explore screens. Choosing a study area should normally open its map, with the summary accessible from About.
- Desktop county view still uses much of the left column for repeated context; only the first couple of candidates fit in the observed 1470×716 window. Keep one concise explanation and move the rest behind help.
- “Need,” “need index,” “canopy priority,” “priority score” and “cooling need” describe the same main result. Use “Priority score,” qualified once as relative within the study area.
- Generated names such as “Coventry Place Apartments SW 12” can sound like actual neighborhood boundaries. Show the city and stable area ID with “near [place]”; keep the map outline central.
- Replace “indicative cost” with “estimated scenario cost”; “canopy points” with “added tree cover”; “rec. mix” with “default priorities.” Put JSON/CSV behind plain task names where possible.
- The contact email now exists on the chooser, resolving the earlier missing-contact concern. Add a direct feedback link to maps, guides and briefings so forwarded recipients do not have to return home.
- Small text and dense toolbars still deserve a physical-phone, text-zoom and screen-reader pass. The sampled modal keyboard loop passes; that is not an accessibility certification.

## Additional export finding

### 13. P2 — Shortlist export does not always match displayed totals

**Confirmed in isolated execution of the actual exporter and scenario functions, with the live county dataset. Shared across all builds.**

`buildShortlist()` and the briefing use a default 25% planting share when a star was added from the list. `cellRecord()` instead requires an existing entry in `plantingShares`, which is normally created when the detail panel is opened. `togglePin()` does not create it. Thus a perfectly ordinary workflow—star an area without opening it, then export the shortlist—can display a scenario total and export blank planting fields.

For county #641, the display calculation at the default share is **513 trees and $256,500**. With no detail visit, the actual exported record has null `planting_share`, `trees`, `trees_surviving`, `canopy_gain_points` and `cost_usd`. This is separate from the one-area save-warning bug above. Tests of `scenarioFor()` arithmetic do not catch this mismatch between its callers.

The same export record omits `access_src`: all-city CSV/JSON field definitions include walking minutes and quality flags but no explicit routed-versus-straight-line field. Current data contains 21 county and 45 Bakersfield residential straight-line estimates. A receiving analyst cannot reliably recover that method distinction from the exported record, while the export's general note describes routed access.

**Fix:** make shortlist display, comparison, briefing and export resolve the effective scenario from one function, independent of whether detail was visited. Decide explicitly whether untouched areas in a full ranking should have no scenario or a default scenario, and explain that scope. Export `access_src` with a generated dictionary entry. Add a regression test for star → export without detail, and for a straight-line fallback's method surviving export.

**Acceptance:** shortlist exported tree/cost totals equal the on-screen totals before and after visiting details; CSV/JSON preserve the walking method for each area.

## Positive findings to preserve

The shared codebase, matched live data, reproducible ranking, explicit source badges, browser-only field notes, source-linked guide, relative-score disclosures, editable priorities, separate official directory, cost scope, survival assumptions and data fingerprints provide a useful foundation for review. The mobile map list is appreciably easier to use than the prior split-view default. No new default-rank arithmetic failure was found.

## Outreach gate

Before sending the homepage broadly: resolve findings 1–3 and the additional export mismatch; correct the resident total, cooling labels and benefit claim; remove current-method contradictions; carry source/coverage into briefings; and verify the resulting release on a phone and in an actual printed PDF. Re-run all-city checks and compare deployed assets to the intended release after changes.

For an earlier guided review, describe it as **an independent exploratory screening prototype seeking feedback on local data, methods, feasibility and usability**. Ask reviewers to validate local fit; do not present their review invitation as evidence that outputs are already validated. A municipal/arborist and methods review is valuable even after all software findings are closed.
