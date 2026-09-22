# CoolEquity outreach-readiness audit

> **Status, September 21, 2026 (after the audit):** findings 1–6, the two sharing defects and the
> map-fit item were fixed and deployed the same day (`advikar/coolequity-app` commit `efacd64`;
> CI and post-deploy smoke passed). The text below describes the release as audited. Still open:
> real-phone check, printed briefing pagination, accessibility pass, non-GitHub contact route,
> free-text custom cost scope, layer/filter/sort state in scenario files.

Audited September 21, 2026, Pacific time (September 22 UTC), against https://coolequity.org/.

## Decision

**Send to BWSI teachers now. Contact city and organization staff for feedback, a demonstration, or a bounded evaluation. Fix the release-integrity findings below before asking them to adopt the exports or use the product routinely. Do not present it as a validated investment recommendation, project budget, or emergency cooling locator.**

This is a functioning, unusually transparent student-built planning screen, with a credible use: helping an analyst assemble candidates for further investigation and discuss how priorities change the list. The product is materially better than the September 13 audit describes. A request for expert review is appropriate now; an unqualified request that officials “use this to decide where to plant” overstates what has been established.

An appropriate initial ask is a 15–20 minute demonstration and feedback on whether a shortlist of three to five areas would help their existing workflow. A subsequent pilot should have a named staff reviewer, one jurisdiction, a small set of candidates, and field verification before decisions.

## Scope and evidence

- Opened the live chooser and all five maps in Chrome. All five populated their ranked lists, with no errors or warnings captured in the sampled map sessions. Checked county detail, editable costs, alternate priorities, sharing and report generation, plus Bakersfield search for a proxy-data cell.
- Retrieved 56 public site assets successfully: chooser; five copies each of app HTML, guide HTML/JS/CSS, cooling directory HTML and ranked data; and five copies each of city configuration, city registry, discovery facilities, designated facilities and boundary geometry.
- The five deployed app HTML files are byte-identical, with city configuration separated from the shared UI. This supersedes the old audit's recommendation to consolidate duplicated applications.
- Executed the actual downloaded browser scoring functions against all five downloaded datasets. **8,435 residential ranks reproduced exactly**, with score differences below 0.05 points, consistent with exported rounding.
- Executed the downloaded scenario arithmetic at 0%, 25%, 50% and 100% planting shares over every cell: **43,440 cases**, no failures in finite cost, nonnegative tree count, street-capacity bound, surviving-tree bound, area bound, or whole-cell future-cover ceiling. This checks arithmetic consistency, not physical feasibility.
- Exercised downloaded CSV and scenario-loader functions in an isolated JavaScript harness. Custom $2,000 cost and 70% survival restore successfully; identified the CSV and field-note issues below.
- Confirmed no duplicate IDs in any guide and no broken app-to-guide fragment targets in the inspected HTML.
- Generated and inspected a live county briefing in the browser. Its map image rendered. Did not certify final PDF pagination or printing across browsers.
- Inspected the public repository's current canopy-validation, stability and jurisdiction code and evidence note, rather than assuming the older local checkout matched deployment.
- Preserved the already-modified local documentation. No product, pipeline, dataset, city branch or public deployment was changed. Audit artifacts and a status note were added only.

**Limits:** this is a broad product/data/code audit, not an accessibility certification, penetration test, raw satellite/lidar reprocessing, independent field validation, every-link crawl, or facility-hours verification. A requested 390 × 844 browser viewport override did not take effect: observed width remained 890px. Accordingly, current mobile behavior is not certified here; responsive code exists but needs a real phone/browser check. The temporary override was reset.

The accompanying `OUTREACH_READINESS_EVIDENCE_2026-09-21.json` records deployed app/data fingerprints and counts. Findings concern that observed release.

## What now works well

- All five builds load and contain coherent rankings; the core question is clear.
- The county ranking changes meaningfully: “Older residents” moved Rossmoor to first place; returning to Recommended mix restored Easter Hill Village NE.
- A source-aware tree-cover display, explicit estimated A/C and walking labels, relative-score explanations, detailed methods, county-designated facility overlays and separate directories provide useful context.
- Rank bands and top-tier stability are now present; the earlier claim that there is no uncertainty analysis is obsolete.
- County canopy coverage has improved dramatically: only five residential cells retain greenness proxies, versus 431 in the earlier audit. Lidar comparison and source calibration are real improvements.
- Custom-cost JSON import, duplicate guide IDs, source-aware canopy CSV nulls, “Has street capacity” wording, separate ranked-row controls, and CSV formula-prefix escaping have been addressed in the deployed implementation.
- Reset now explicitly clears ranking filters/sort and restores cost and survival. This is source inspection, not an exhaustive interactive reset test.
- City/community filters, comparison/shortlist code, field checks, cost bands and survival assumptions have been added. More features are not the immediate prerequisite for outreach.
- Most chooser statistics reproduce approximately from the shipped data: county average canopy rounds to 18%; Bakersfield median surface heat to 122°F and residents below 15% canopy to 93%; West County and Pittsburg/Bay Point have approximately half their residents in sub-10%-canopy cells.

## Fix before an operational pilot

### 1. High: exported CSVs do not carry enough scenario context and contain a duplicate city column

**Affected:** shared app, all five builds.

`toCsv()` repeats weights and data metadata, but omits unit cost, survival share, crown area, spacing and the cooling coefficient. The guide promises that every export carries planting constants and that the chosen unit cost is written into every export. This is false for CSV. Some quantities can be inferred from nonzero rows, but that is not a reliable schema, particularly for zero-planting rows.

`EXPORT_FIELDS` and the appended metadata both contain `city`. `FIELD_KEY` also defines `city` twice, so the intended `city_or_community` name is overwritten. The resulting CSV has two `city` headers, and both receive the cell's city because record fields take precedence over header fields. The study-area slug is lost from those columns. Duplicate headers cause ambiguity when opened in analysis software.

**Acceptance:** export a scenario with a nondefault unit cost and survival rate; the CSV must have unique headers, separate `city_or_community` and `study_area_slug`, and explicit scenario/model assumptions on every row. A colleague must be able to reproduce the outputs without inferring settings from rounded results.

### 2. High: greenness export is numerically on the wrong scale

**Affected:** shared export code; demonstrated in Bakersfield, whose dataset has 62 residential proxy cells.

Live search for area **105, Southland R.V. Park W 24**, displays **55/100 greenness**. The deployed `cellRecord()` exports **24.6** in `greenness_index`, whose CSV name and column description promise `greenness_index_0_100`. The stored value uses the internal 0–45 scale; the UI correctly computes 24.6 / 45 × 100 ≈ 54.7.

**Acceptance:** export the same unrounded 0–100 value used by the display; verify several nonzero proxy values and keep unavailable canopy null. County and West County's remaining proxy values happen to be zero, which masks this defect there.

### 3. High for fieldwork handoff: reopening a scenario ignores field-check records

**Affected:** shared scenario loader, all builds.

`cellRecord()` saves status, note and update time. `loadScenario()` restores weights, cost, survival, planting shares and selection, but never reads field-check fields. The loader can report successful loading and identical data while a colleague's browser shows no imported field evidence. The note remains in the JSON file; it is not restored into the workflow.

Shortlists and complete view/filter state are also not serialized/restored as an exact view. The interface's “exact view” language should be narrowed or implemented.

**Acceptance:** save a scenario containing a nonempty field note and status; load it in a fresh browser profile and verify the same record appears, with a clear conflict policy for existing local notes. Round-trip shortlist membership if it is part of the saved-scenario promise.

### 4. Medium, credibility-sensitive: the generated briefing misstates sources and parts of the model

**Affected:** shared report generator, visibly verified in county report.

The report's source table says population is allocated by **residential footprint**, whereas the county guide and implementation use **area allocation**. It lists canopy solely as USFS/CAL FIRE 2022 aerial classification, although most county residential cells now use a calibrated height model or lidar. The limitations elsewhere partly qualify this, leaving the report internally inconsistent.

It says every input is scaled between p2 and p98, but the shipped normalizers and guide describe asymmetric clipping by input. Population's multiplier is described as multiplication by the number of residents, although the implementation uses a bounded normalized-population factor. These are fixable explanatory errors.

The shortlist report template labels a proxy number as “Tree cover” and can say trees cover an `/100` index of the ground. It also shows default-model rank bands beside custom-model ranks without the detail panel's immediate “under the recommended mix” qualifier. These are source-confirmed template issues; the generated sample had no shortlisted proxy cell.

**Acceptance:** generate briefings for county area allocation, a proxy cell, and custom weights. Every metric, rank interval, source, unit, assumption and demographic method must agree with the selected build and active scenario.

### 5. Medium: cost scope changes in the explanation but not the scenario label

**Affected:** all builds.

The tooltip/guide describe Base $2,000 as including establishment care and High $3,500 as including three years of watering/program costs. Selecting Base updates the top county scenario to **$1,026,000 for 513 trees**, but the detail still says **“planting only”** and explicitly excludes establishment watering and maintenance. JSON notes also retain a hard-coded $500 sentence even when structured assumptions record a different amount. The report substitutes the price but preserves the planting-only interpretation.

These bands are useful benchmarks, but their source programs cover different services. A grant total divided by trees is not a locally validated marginal tree price.

**Acceptance:** retain cost scope alongside the numeric price, make custom scope explicit, and propagate both consistently through detail, CSV, JSON and briefing. Clearly distinguish illustrative program averages from local quotes. Consider opening with the base scenario or showing the cost range together rather than anchoring the headline at the lowest band.

### 6. Medium: source and methodology copy has drifted across the site

**Affected:** chooser, shared UI/report and city guides.

Examples verified in the live files:

- The chooser says tree cover in every build comes from the 2022 aerial classification with a greenness fallback. It omits the height-model and lidar paths; **1,456 of 2,697 county residential cells use those two paths**.
- The county Population topic says ACS margins of error are “not yet propagated,” while its rank-stability topic and actual dataset describe propagation.
- The cost topic says survival is not modeled despite an explicit survival assumption now affecting outputs. It should distinguish an assumed survival fraction from a predictive survival model.
- County geography text says 2,695 residential / 8 activity / 156 empty; live data has **2,697 / 7 / 155**.
- The chooser's San Ramon heat/canopy correlation is −0.60; Pearson correlation over all shipped residential cells is approximately **−0.668**. State the exact subset/method behind the headline or regenerate it.
- Source years and release metadata are inconsistent: the county data has a September 13 stability computation but the app version tag remains `20260909-walk`, and the chooser says updated September 10. The SHA-256 fingerprint is useful, but human-readable release dates should also match.

**Acceptance:** generate summary counts/claims from the released data where possible; check all five guides, root copy, popovers and exports together. Correcting the most prominent statements is sufficient for initial outreach; do not defer outreach indefinitely for historical documentation cleanup.

## Sharing: improved, with two remaining defects

The old blanket finding that a share link promises to preserve planting shares is no longer accurate: the export panel and toast now say links carry priorities, layer and selection only. Keep that narrower contract.

However, the Share tooltip still says “exact view”; custom normalized weights are rounded to whole percentages, which can change rankings. `applyHash()` explicitly skips `access` and `holc` layers, despite the promise to preserve the layer. URLs lack a data fingerprint, so future data releases can produce a different result at the same link.

For teacher review this is not a blocker. For reproducible collaboration, preserve sufficient precision, honor supported layers, identify the data/model revision, and reserve “exact” for state that is actually serialized.

## Data readiness and limits

Counts below are from residential cells only. “Full aerial” means the app's ≥99% assessed-coverage gate, **not 99% accuracy**. The five areas overlap geographically and their populations must not be added together as unique people served.

| Build | Ranked cells | Full aerial | Partial aerial | Height model | Lidar substitute | Greenness proxy |
|---|---:|---:|---:|---:|---:|---:|
| Contra Costa County | 2,697 | 794 | 442 | 1,330 | 126 | 5 |
| Bakersfield | 3,767 | 1,959 | 287 | 1,459 | 0 | 62 |
| San Ramon | 419 | 356 | 53 | 2 | 8 | 0 |
| West Contra Costa | 982 | 818 | 149 | 7 | 7 | 1 |
| Pittsburg & Bay Point | 570 | 398 | 104 | 52 | 16 | 0 |

The county's 1,330 height-model cells are calibrated. Bakersfield's 1,459 height-model cells retain unknown assessed coverage and are outside the county lidar reference. The county lidar comparison improves confidence in broad canopy patterns; high correlation and calibration do not independently validate exact project priorities or planting outcomes. No held-out field validation was established by this audit.

Rank stability varies ACS/LACE estimates and policy weights, while holding canopy, heat, walking time and within-block-group population allocation fixed. Describe these as **sensitivity bands under stated assumptions**, not comprehensive confidence intervals or validated probabilities that a rank is correct. “Rank differences smaller than the band are noise” is too categorical: overlapping marginal intervals are not a formal pairwise test.

The walking layer still targets mapped discovery facilities, rather than solely verified designated services. County data flags 2,238 of 2,697 residential cells for a >100m off-network approach and 34 for detour review. These flags do not prove the routes are wrong, but the resulting minutes cannot be presented as verified accessible door-to-door travel. The separate designated overlay and call-before-going directory are helpful and should stay clearly separate from this score input.

Street length establishes theoretical scenario capacity. Ownership, utilities, existing-tree spacing, soil, irrigation, survival, species and maturity horizon still require local verification. The composite score estimates relative resident-oriented need, not marginal benefit per dollar. A consistent ranking can still be based on imperfect inputs or policy choices.

Jurisdiction filters are useful but assign full analysis cells by centroid. The San Ramon build labels some edge cells Danville, Dublin or unincorporated; the county build includes labels from adjacent counties. This does not by itself prove bad data: border-crossing cells and unclipped centroids can cause it. Make boundary treatment clear and validate totals and inclusion rules with the pilot jurisdiction before staff use it for jurisdiction-specific reporting.

## Usability, accessibility and adoption

The desktop visual system is coherent; the ranked list, explanations, source tags and direct map entry are useful. At the tested 890px width, however, opening a build produced a small study-area footprint within a much larger regional map, and top controls crowded the share chip. `fitData()` reserves 360px at the right even when no detail panel is open. Fit to available map space and reserve that width only when a panel actually needs it.

Source-aware row controls are now separate buttons, which improves the earlier nested-button problem. Keyboard focus is visible in sampled interactions. Dense small text and numerous controls still need a proper keyboard, screen-reader, contrast, zoom and mobile pass; no accessibility compliance claim is supported by this audit.

Public-facing identity and support would benefit from a short About/contact section: named maintainer, student-project context, purpose, last release date, feedback route that does not require GitHub, and a plain explanation of local-only field notes. Do not imply BWSI, city or county endorsement. GitHub issues work for developers but are a poor sole contact route for busy officials.

No backend account is required for the main map, which keeps a trial simple. The app reports local-only field notes, but externally hosted basemaps still require requests to third-party services; avoid describing ordinary online use as entirely offline or making an unqualified privacy certification. An organization considering adoption will also need ownership/support expectations, data-refresh cadence and a software/data-license inventory. These are adoption questions, not prerequisites for asking a teacher for feedback.

## Outreach sequence and acceptance criteria

1. **Now: BWSI teachers.** Send the site as student research/software work and ask for methodological critique, a short demonstration, and introductions to a relevant practitioner. Be candid that field verification and operational handoff fixes remain.
2. **Now: one or two relevant officials or organizations.** Ask whether the screening workflow addresses a real task they have. Link their specific city build. Avoid a mass request for adoption.
3. **Before a staff pilot:** fix findings 1–6, finish scenario/field-note round trips, verify one representative mobile session and a printed briefing, and publish a concise changelog. Do not add another city to solve these release issues.
4. **Pilot:** jointly inspect a small, stratified sample of high- and lower-ranked cells, including mixed/partial-source cases. Record corrections, utility to staff, failure modes and time saved. Ask for the actual local cost scope and facility/service requirements.
5. **Before operational reliance:** agree on accepted uses, validation criteria, update/support ownership and limitations. Keep candidate screening separate from approved planting sites, approved budgets and public emergency guidance.

Suggested positioning: “CoolEquity is an exploratory tool for identifying areas to investigate for shade investment. I would value your feedback on whether its shortlist, source information and adjustable priorities could support your team's existing assessment process.”

## Primary evidence links

- [Live chooser](https://coolequity.org/)
- [County map](https://coolequity.org/contracosta/app/?go=1), [guide](https://coolequity.org/contracosta/app/guide.html), [data](https://coolequity.org/contracosta/data/contracosta.geojson)
- [Bakersfield map](https://coolequity.org/bakersfield/app/?go=1), [data](https://coolequity.org/bakersfield/data/bakersfield.geojson)
- [San Ramon data](https://coolequity.org/sanramon/data/sanramon.geojson), [West County data](https://coolequity.org/westcc/data/westcc.geojson), [Pittsburg/Bay Point data](https://coolequity.org/pittsburg/data/pittsburg.geojson)
- [Project evidence note](https://github.com/advikar/coolequity-app/blob/main/docs/EVIDENCE_COST_CANOPY_2026-09-13.md), [canopy-validation implementation](https://github.com/advikar/coolequity-app/blob/main/pipeline/02f_canopy_validate.py), [stability implementation](https://github.com/advikar/coolequity-app/blob/main/pipeline/05b_stability.py)

The repository evidence note is the project's own account; this audit inspected its implementation but did not independently reproduce the raw-data calibration or all third-party source claims.
