# CoolEquity re-audit: accuracy, release readiness and usability

> **Status, September 22, 2026 (after the re-audit):** findings 1–7, 9 and 10 were fixed and
> deployed (`advikar/coolequity-app` commit `4c3b229`; CI, deploy and the new release-stamped
> smoke check passed). The stability pipeline now smooths the age share once and all five
> builds were re-run. The text below describes the release as audited. Still open: finding 8
> (layout), the wording table, physical-phone and printed-PDF passes. See `STATUS.md`.

Audited September 21, 2026 Pacific / September 22 UTC. Requested after Claude's fixes to the previous audit.

## Verdict

**The live site is suitable for a guided demonstration and explicitly exploratory feedback. It is not yet ready to be called a clean, independently usable review release.** Fix the failed build, rank-sensitivity calculation, save-warning gaps and accessibility issues below first. The core default ranking and planting arithmetic pass their current contracts; the new sensitivity finding does **not** establish that the main rankings are calculated incorrectly.

The deployed source is `../coolequity-app`, not this older per-city-branch repository. Its local and remote `main` are `86201f6b70bbe68af30fa4cef60682f599d1f594`. That commit's Actions run failed. The preceding `a89da99fcfc87735277a06b4567e0d5e08fa8cf8` passed. The live site still works because it serves the preceding successful release.

No app, pipeline, dataset or city branch was changed or deployed during this audit. Only this report, its evidence manifest and a STATUS entry were added in the older audit repository. All five study areas were inspected: Contra Costa County, Bakersfield, San Ramon, West Contra Costa, and Pittsburg & Bay Point.

## What was actually verified

- Ran `PYTHONDONTWRITEBYTECODE=1 bash scripts/test.sh` in `coolequity-app`: all five JavaScript contract groups passed; **8,435 residential default ranks** match the shipped data; **43,440 scenario cases** passed; **45 Python tests** passed (nine per city). The subsequent site build **failed**, so the full suite is not green.
- Downloaded **56 live assets**, all HTTP 200: chooser; each city's app, guide, guide scripts/styles, cooling directory, city settings, registry and four datasets. All 55 city assets match the local source after removing only the injected analytics script where applicable. The chooser differs by analytics injection and its privacy sentence. Dataset bytes match exactly. Fingerprints are in the companion evidence file.
- Opened all five live maps in the in-app browser. Inspected county detail, Base cost preset, reset, Bakersfield's proxy cell 105, city switching, San Ramon custom priorities and the reset dialog. No errors/warnings appeared in the captured in-app browser log sample.
- Visually inspected county desktop at 1280×720 and phone emulation at **390×844**, with actual `innerWidth=390` and document width 390. Detail, List, Both and Map views render; no page-wide horizontal overflow occurred in that phone sample. This improves on the previous audit, whose viewport override did not work. It is still not a physical iPhone/Android test.
- Measured the light-theme explanation contrast from computed browser colors; tested keyboard focus escaping a modal.
- Verified cost-only reset loss in the browser. A separate isolated execution of the actual loader reproduced imported planting shares not being marked dirty.
- Generated a live county briefing in Chrome and inspected its actual content, including source counts and area-based population allocation. Print-preview interaction stalled; **final PDF pagination is not verified**. The in-app browser did not expose a new report tab, so embedded-browser report support also remains unverified.
- Independently isolated the second age-smoothing operation in a read-only calculation against all five datasets. Baseline ranks reproduce exactly before the extra operation.

These checks are implementation and product checks, not field validation, a complete security assessment, an accessibility certification, or a rebuild from raw satellite/lidar/census inputs. Existing tests do not validate whether the sensitivity distribution is centered on the intended model.

## Findings to fix

### 1. P1 — Latest main cannot build or deploy

**Evidence:** `coolequity-app/site/goatcounter.txt:1` contains `YOUR-CODE`, both locally and in HEAD. `scripts/build_site.py:43` accepts only lowercase letters, digits and hyphens. The suite stops with `site/goatcounter.txt must hold a site code ... not 'YOUR-CODE'`. The public Actions API confirms the latest commit failed; the preceding commit passed.

**Impact:** every new release based on current main fails until this setting is corrected. The existing live site is still available; this is not a live outage.

**Proposal:** restore the verified preceding configuration, or intentionally disable analytics with an empty file. Do not guess a new account code. Run the complete suite and publish a new successful revision. Improve smoke testing to check a release identifier/content fingerprint, rather than HTTP 200 alone: an old release also returns 200.

**Acceptance:** complete all-city suite, clean build, successful deployment, then verify live app/data/release metadata against the intended revision.

### 2. P1 — Rank-sensitivity calculation smooths the age share twice

**Evidence:** `pipeline/05_score.py:264` smooths raw age share and exports the smoothed result as `pct65` at line 342. `pipeline/05b_stability.py:144` starts from that exported, already-smoothed `pct65`; line 170 applies `shrink_age65()` again after the draw. Even with population/age draw factors of one, it changes the baseline age input. The second shrink is strongest for small populations and therefore is not simply a constant rescaling that disappears during normalization.

A diagnostic that holds all other inputs, weights and **published bounds** fixed isolates the extra smoothing:

| Study area | Ranks changed by extra smoothing | Largest rank change | Median absolute change |
|---|---:|---:|---:|
| Contra Costa County | 2,460 / 2,697 | 412 | 8 |
| Bakersfield | 3,668 / 3,767 | 953 | 24 |
| San Ramon | 378 / 419 | 58 | 4 |
| West Contra Costa | 924 / 982 | 72 | 8 |
| Pittsburg & Bay Point | 532 / 570 | 125 | 6 |

These are **diagnostic changes caused by the isolated extra operation**, not corrected production ranks or forecasts of how much each published interval will move after a rebuild. Example: Bakersfield cell 2559 has 107 residents and a published smoothed age share of 43.2%; the second smoothing lowers it to about 27.69% before any uncertainty is introduced.

**Impact:** the `Likely rank` intervals, top-tier shares, stable-top-tier filter and guide summaries cannot currently be trusted as sensitivity of the stated single-smoothed ranking. Main rank parity still passes.

**Proposal:** start uncertainty propagation from raw allocated population/older-resident counts, carry each draw through the same allocation and smoothing path exactly once, and share the scorer with the main pipeline. Review the overlap-area weighting used in 05b against each city's population/housing allocation, rather than assuming it reproduces those allocations. Do not merely delete smoothing from the stochastic pipeline without defining the intended raw-input model.

**Acceptance:** a no-uncertainty/no-weight-jitter case reproduces the intended point model within documented rounding policy; tests cover a small-population, high-age cell; rebuild all five sensitivity outputs and their guide statistics. Until then, hide or explicitly mark the sensitivity feature as under correction.

### 3. P2 — Cost/survival edits and imported shares can be lost without a save warning

**Evidence:** `app/index.html:1898`, `isDirty()`, checks only nondefault weights or `userShares.size`. Cost and survival handlers at lines 1856–1858 do not mark the scenario dirty. The loader restores `plantingShares` but does not populate `userShares`.

Browser reproduction: open county area 641, choose Base $2,000, close detail, Reset map. No save dialog appears; reopening shows $500 and cost falls from $1,026,000 to $256,500. An isolated loader check accepted default weights plus an 80% planting share and $2,000/tree, while `isDirty()` returned false.

**Proposal:** track unsaved scenario changes against a saved baseline, including cost, survival, imported shares and custom assumptions. Account for successful saving so users are not repeatedly warned about unchanged saved work. Keep durable field notes/shortlists distinct from transient scenario settings.

**Acceptance:** independently change cost, survival and an imported share; reload/reset/leave must preserve work or offer a clear save choice. Do not use mere area selection to trigger unnecessary warnings.

### 4. P2 — Important light-theme explanation text is difficult to read

**Evidence:** `.explain .why` at `app/index.html:421` resolves to RGB(255,183,3), on RGB(246,248,250), at 12.5px. Contrast is **1.64:1**. The affected phrase is the key explanation of why an area ranks highly, not decoration. The standard minimum for this normal-size text is 4.5:1 ([W3C contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)). The desktop and phone screenshots both visibly show pale yellow words on a pale card.

**Proposal:** use a dark brown/orange semantic text color in light mode; retain brighter accents for dark backgrounds. Check comparison highlights and field-status colors too, which also contain hard-coded light colors. Increase reading text and critical labels rather than relying on users zooming in.

**Acceptance:** computed contrast at least 4.5:1 for normal text in both themes, including selected, warning and field-status states; inspect 200% zoom and keyboard focus.

### 5. P2 — Reset/save modal lets keyboard focus escape behind it

**Evidence:** the reset dialog declares `aria-modal=true` but has neither focus containment nor an inert background. In San Ramon, choose Trees only → Reset map. Focus starts on Save scenario & reset; Tab leaves the dialog and the next Tab reaches the background Home button while the dialog remains open. `wireLeave()` at `app/index.html:1925` handles Escape only.

**Proposal:** use a native modal dialog or implement a complete focus loop and inert background. Restore focus to the actual invoking control. Apply the same pattern to shortlist clearing; its modal follows a similar implementation.

**Acceptance:** Tab/Shift+Tab remain inside each open modal, Escape closes it, and focus returns to the trigger. Check with a screen reader. This follows the [W3C modal-dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/).

### 6. P2 — CSV column guides still describe the old export format

**Evidence:** all five live `guide.html` export tables still say `city` is the city slug and `scenario_cost_usd` is cost at $500/tree. They do not contain `study_area_slug` or `scenario_trees_surviving`; `scenario_trees` is listed instead of the current `scenario_trees_planted`. The actual exporter was fixed and uses the new fields and chosen cost.

**Impact:** a reviewer following Column key gets incorrect instructions even though the exported values are now improved. This is an incomplete follow-through on the previous source/copy audit, not a regression in CSV arithmetic.

**Proposal:** generate the displayed column dictionary from the same field definitions used by the exporter, including appended metadata and units. Define `canopy` source type broadly enough to include height-model and lidar paths; its current field description says aerial assessment only.

**Acceptance:** compare actual headers against every guide dictionary; no missing, renamed or incorrectly described current fields. Export at a nondefault cost and survival rate when checking.

### 7. P2 — Compare table omits the default-model qualifier on rank bands

**Evidence:** `compareTable()` at `app/index.html:2966` labels a row simply `Likely rank`, while the column badge uses the current `rk(p)`. Thus a custom-priority comparison combines current ranks and stored recommended-mix bands. The detail panel and report have qualifiers; comparison does not.

**Proposal:** label the row `Rank range · default priorities`, and show the active-priority label above the table. After correcting finding 2, prefer `Sensitivity range` over `Likely rank`, with a plain explanation available nearby.

**Acceptance:** compare two areas under Older residents/custom weights and verify that no default-model range appears to describe that custom ranking.

### 8. P2 — Phone split view and desktop information hierarchy impede the first useful action

**Observed:** at 390×844, Both leaves approximately half the screen for the map, then fills much of that half with a multi-line status/share chip, reset/basemap controls and a tall explanation/legend. It renders without horizontal overflow, but the visible map is cramped. At the initial 1280×720 desktop view, the first ranked candidates fall below the fold because the introduction, repeated explanation and weights occupy the left panel.

**Proposal:** default phones to List, retain an obvious Map switch, and collapse the legend to a short color bar. Use a single compact map toolbar. On desktop, show the study-area selector, search and first candidate rows immediately; put custom weights below a concise preset selector or behind Adjust priorities. Preserve the detailed methods through contextual help instead of repeating them in three places.

**Acceptance:** a new user can find an area, open its details and add it to a shortlist without learning the weighting model or scrolling through explanatory paragraphs. On a physical phone, test typing with the keyboard open, touch targets, detail back-navigation, orientation change and zoom.

### 9. P2 — Briefing is not yet a verified, consistently scoped handoff

The prior source corrections are present: the county report now says overlap-area population allocation and counts the actual canopy source paths. However:

- Its headline/intro still says every area is scored on all inputs, even when heat and walking time have zero weight. Generate a short active-input summary instead.
- Its cover captures the current map viewport/layer, while its table uses the full `LIVE.order` top 25, independent of city filters/search. That behavior needs an explicit scope label; a zoomed/filtered map can otherwise look like it supports the same subset as the table.
- The toolbar promises a fixed three pages (four with a shortlist), although content length and shortlist size vary. CSS puts the whole shortlist in one `.page` wrapper. Do not promise a fixed count without controlling pagination.
- The top-25 table uses `Trees` for both percentages and proxy `/100` values; shortlist text is better qualified. Use explicit units/source-aware labels in the table too.

**Acceptance:** actually print/save Letter PDFs with 0, 1 and 6 shortlisted areas, long notes, a proxy cell, custom weights, and a jurisdiction filter. Verify every row, footer, page break, map scope, unit and source. This audit generated and read the Chrome HTML report but could not complete print-preview verification; it does not assert a demonstrated printed clipping defect.

### 10. P3 — Analytics changes the offline contract and privacy copy needs precision

The build injects the external GoatCounter script unconditionally into all app pages, including `?flat=1`. The old promise that flat mode makes zero off-host requests no longer holds. The map may still work offline; that is different from making no network requests. README says optional/off by default and byte-for-byte copying while the deployed build has analytics injection.

**Proposal:** skip analytics on the explicit offline rehearsal path and update the build/offline documentation. Replace the absolute “no personal data” statement with a precise description of aggregate page-view analytics and a link to the provider's policy. GoatCounter documents aggregate browser/system/location/screen-width data and temporary in-memory processing of IP and user-agent information ([provider policy](https://www.goatcounter.com/help/privacy)); account-specific settings were not inspected here. No upload of field notes was observed or alleged.

**Acceptance:** `?flat=1` passes an off-host-request test if that contract is retained; privacy wording matches the configured behavior.

## Proposed wording changes

These are proposals, not edits already made. Keep the strong source distinctions and explicit assumptions.

| Current wording | Proposed wording | Reason |
|---|---|---|
| Where would new trees help residents most? | Find areas to investigate for new shade trees. | The score measures relative need; it does not estimate which investment produces the greatest benefit. |
| Recommended mix | Default priorities | Avoids implying external or professional endorsement of project-chosen weights. |
| Trees only | Prioritize low tree cover | This preset still uses population; “only” is misleading without reading the explanation. |
| Far from cooling / Walk to cooling | Long walk to mapped facilities / Estimated walk to a mapped facility | The discovery sites are not verified emergency cooling services. |
| Places to cool off | Cooling locations & mapped facilities | Allows two clear subgroups: County-listed cooling sites; Other mapped facilities. |
| Likely rank | Rank sensitivity range · default priorities | Avoids implying comprehensive statistical confidence; use after fixing the calculation. |
| Need / need index / priority score / canopy priority | Priority score | One term across list, detail, legend and report, with “relative within this study area.” |
| People 45% | Population influence: 45% | Makes it visibly separate from additive weights that already sum to 100%. |
| +1.9 percentage-point canopy gain | Estimated added tree cover: +1.9 percentage points | Plainer; immediately show “5.3% today → 7.2% at maturity” only where the baseline supports it. |
| How many street trees could fit here | Explore a planting scenario using mapped street length. | Avoids suggesting surveyed feasibility. |
| Full aerial tree data | Aerial coverage ≥99% | Says what the filter actually tests; explain that coverage is not accuracy. |
| Briefing report (PDF) | Open printable briefing | The button opens HTML, followed by a print/save step. |
| Save scenario (JSON) | Save scenario file | Put the file type in secondary text. |
| Ranking (CSV) | Download all ranked areas | Make export scope unambiguous even while the list is filtered. |
| Reply to whoever sent you this link | A direct Feedback/contact route supplied by the owner | Direct visitors and forwarded recipients may not know who to contact. Do not invent an address. |

## Suggested interface arrangement

Retain the map, source-aware details, presets and shortlist. A wholesale redesign is unnecessary.

1. **Find:** study area, city/community filter and search at the top. A short purpose statement and data date nearby.
2. **Review candidates:** first candidate rows visible immediately. Show rank, consistent score label, estimated residents and a compact source indicator. Label ground temperature explicitly as surface temperature.
3. **Adjust priorities:** a small preset selector with Default priorities selected and an Adjust button. Explain the active weights once; keep the population influence separate.
4. **Inspect an area:** why it ranks → data and source quality → optional planting scenario → field notes. Prefer a readable two-line heading to cramming name, rank, city, ID and sensitivity into one small block.
5. **Build a shortlist:** a labeled Add to shortlist button in detail; unique accessible names such as “Add Easter Hill Village NE to shortlist” on row stars. Keep comparison and saving easy to discover.
6. **Take it away:** a persistent Save/Export entry point, with clear choices for all areas, visible results, shortlist and selected area. Files and links preserve different state; explain that at the choice itself.

For costs, show low/base/high together or name the selected scope beside the headline price. These bands cover different services, so do not present them as a statistical uncertainty interval. Keep the default value a deliberate product choice rather than silently changing the financial assumption during a visual redesign.

## Remaining data limitations that wording cannot solve

- Street length remains theoretical capacity, not permission or site feasibility; field checks are still needed.
- Discovery-facility walking estimates are not verified routes to open designated services. County-listed directories are a separate source.
- Canopy source vintages/coverage differ; calibrated height-model data is not equivalent to new aerial observations. Mixed-source filters and labels should remain.
- City/community assignment uses cell centroids; border cells can be labeled as neighboring jurisdictions. A filter is not a clipped municipal population total. Put a short boundary note by jurisdiction filters/exports.
- Population/age are allocated estimates. The displayed age share is also smoothed; do not describe the resulting estimated older-resident count as a raw Census headcount.
- Scores are within-study-area comparisons; the overlapping county/subarea populations must not be added as unique people served.

## Release gate and recommended order

1. Restore a valid build configuration.
2. Correct/rebuild sensitivity or temporarily remove its claims and filter.
3. Fix scenario save protection, contrast and modal focus.
4. Regenerate export dictionaries and qualify comparison bands; tighten prominent copy.
5. Simplify first-use desktop/phone layout and complete actual printable briefing and physical-phone checks.
6. Run all-city contracts/build, focused regressions for each finding, and live revision verification.

After those checks, invite unassisted reviewers to complete five tasks: find their jurisdiction; explain why one candidate ranks highly; distinguish source quality; shortlist three candidates; save and reopen that work. Record where they hesitate. This is a more meaningful usability gate than whether the map simply loads.
