# Cool Equity active handoff

Updated: September 8, 2026. Latest task: model allocation and publication planning.

## Current task state

- Planning complete; implementation packets in DELIVERY_PLAN.md have not been run.
- Next active packet: CE-01 baseline/checkpoint. After it, CE-07 build-only repair
  can proceed while the documentation/data review queue is planned.
- Checkout inspected: `contra-costa`, HEAD `0350f8a`.
- Existing product/data work is dirty and unpublished per the latest project notes.
  Inspect the current git status; do not discard or automatically stage all changes.
- This planning task added DELIVERY_PLAN.md and HANDOFF.md and a STATUS entry only.
  No product behavior, dataset, deployment script or other city branch changed.
- No tests rerun in this planning task. September 8 prior validation is recorded
  in STATUS.md; distinguish it from new verification.
- Concrete discovered release gap: deploy.sh does not package
  data/cooling_directory_contracosta.json. It archives committed branches, so it
  will also omit current uncommitted work. Do not run it just to preview a build:
  it ends by force-pushing gh-pages.
- No implementation process was started by this planning task. Check for any
  pre-existing processes before taking over.

## Next action

Read AGENTS.md and DELIVERY_PLAN.md. Inspect git status and relevant diffs; verify
the current branch/head. Preserve existing rebuild baseline and reports. Run:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
node tests/ui-contract.cjs
git diff --check
```

Record actual results and any environment blockers. Review the existing changes
before creating a checkpoint; do not overwrite another agent's work. Then prepare
CE-07's artifact build/asset manifest and smoke checks without publishing.

## Checkpoint — September 8, 2026 (Claude): scenario export (CE-06) on all three v2 branches

Two exports in the map, both reproducible, plus a loader: **Export this area** (JSON/CSV, in
the selected-area panel) and **Export ranked list** / **Scenario (JSON)** / **Load scenario…**
(under the ranked list). Every export carries the weights in force, population weight, preset
(if any), planting constants, per-cell source/coverage flags (canopy_source, coverage_frac,
canopy_quality, ac_src, ac_coverage, access_quality), live rank/score and the pipeline defaults,
the planting scenario for cells with a set share, and the SHA-256 of the loaded data file
(computed in-browser at load; "unavailable" on file://). CSV rows repeat the scenario header
as trailing columns. Loading a JSON export restores weights, population weight, planting
shares and the selection; it refuses another city or export schema and warns visibly when the
data fingerprint differs. Nothing is uploaded. Scenario arithmetic moved into `scenarioFor()`
so the panel and the export share one implementation. Guide topic `#export` added.
Verified: `node tests/ui-contract.cjs` (new export section), inline-script syntax, browser
smoke. Same change applied to contra-costa, bakersfield and san-ramon.

## Checkpoint — September 8, 2026 (Claude): deploy guardrail; San Ramon replicated

- Root cause of the evening outage: the bakersfield worktree still carried the old
  two-city deploy.sh (a copy step in my port had failed silently) and my instructions
  pointed the user at it; the resulting gh-pages build dropped Contra Costa and
  Bakersfield. Repaired by a four-city redeploy (user ran it). All four cities verified 200.
- Guardrail (commit b0ef63d on contra-costa, synced byte-identical onto master,
  san-ramon, bakersfield): deploy.sh aborts unless identical to contra-costa:deploy.sh,
  aborts if the assembled site has fewer city folders than the live one, and notes any
  local/remote drift per branch. Tested: a modified copy refuses to run.
- San Ramon port committed on `san-ramon` (worktree ../coolequity-sanramon). See STATUS.md
  there. Kept dasymetric population placement; pipeline mask-guard scope fixed; documented
  DASY_MAX_INCOME_BIAS=3.0 override with evidence. Baseline preserved at
  ../coolequity-sanramon-baseline/.
- Pushes were blocked for this session: master, san-ramon, contra-costa, bakersfield are all
  ahead of origin and need `git push origin <branch>` from the user, then `./deploy.sh` from
  the contra-costa checkout to publish San Ramon.
- Back-port candidates for contra-costa (no behaviour change there): boundary clip in 03,
  lace-pop fallback, canopy_m2 2 dp, mask-guard scope, config-driven 06/tests.

## Checkpoint — September 8, 2026 (Claude): Contra Costa deployed; Bakersfield replicated

- Contra Costa: user ran `./deploy.sh`; live contracosta/app/{guide,cooling}.html return 200
  and render (gh-pages built from contra-costa 96963b1). Review of Codex's commit: pipeline,
  data and UI changes are coherent and pass its own suites; hardcoded slug/copy noted below.
- Bakersfield replication done in a separate worktree
  `../coolequity-bakersfield` (branch `bakersfield`), so this checkout is untouched.
  See STATUS.md on that branch for the full entry. Summary: Contra Costa app v2 + guide +
  cooling directory ported; pipeline 02b/02c/02d/03/04/04b/05/06 + cooling_sources + tests
  ported; full data rebuild on ACS 2024; Kern County cooling directory (10 centers).
- Defects found in the ported pipeline that matter for any non-county city branch:
  (1) 03_census.py lost the clip-to-boundary step for area weighting → 12% overcount on
  Bakersfield; restored under `if C.BOUNDARY_FILE.exists()`. (2) Housing-weighted LACE
  yields no rate where a block group has residents but zero occupied homes; the income
  fallback then stretched the A/C normalisation. Added a `lace-pop` fallback for that case.
  (3) canopy_m2 rounded to 0 dp can store a single pixel as 0 → now 2 dp. Consider
  back-porting (1) and (3) to contra-costa; (1) is a no-op there, (3) is harmless.
- 06_audit_rebuild.py on bakersfield is generalised (weights from config incl. heat, slug
  from config); tests parametrised on config.SLUG. Contra Costa copies still hardcode.
- Checks on bakersfield: unittest 7/7 OK; ui-contract PASS; node syntax OK; diff --check OK.
- Not deployed. Next: user confirms → commit is on `bakersfield`; push branch; `./deploy.sh`;
  verify https://advikar.github.io/coolequity/bakersfield/app/guide.html.
- Baseline (pre-rebuild) Bakersfield data preserved at `../coolequity-bakersfield-baseline/`.

## Checkpoint — September 8, 2026 (Claude, CE-01 baseline + CE-07 dry build)

- Active packet and acceptance criteria: CE-01 baseline checkpoint; CE-07 build packaging
  check without publishing. Goal: make the Codex guide UI (app/guide.html, guide.css,
  guide.js, cooling.html) visible on the live Contra Costa site.
- Owner/model and branch/head: Claude (Fable 5.1); `contra-costa` at 96963b1, clean
  working tree, in sync with origin/contra-costa.
- Files and city branches changed: HANDOFF.md only. No product code changed.
- Completed changes and preserved decisions: Root cause of "guide not visible" is that
  gh-pages was last built from contra-costa 0350f8a (before the guide commit); live
  contracosta/app/guide.html and cooling.html return 404. deploy.sh already archives
  the whole app/ dir, so it needs no change to ship the guide. The map does not fetch
  data/cooling_directory_contracosta.json at runtime (cooling.html inlines the
  directory), so the earlier noted deploy gap is not a runtime blocker.
- Commands run and exact pass/fail summary:
  `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'` → 7 tests OK;
  `node tests/ui-contract.cjs` → PASS (3 groups); `git diff --check` → clean.
  Dry build (deploy.sh archive steps only, no push) contains
  contracosta/app/{index,guide,cooling}.html, guide.css, guide.js, vendor/, and the
  three data files.
- Unverified behavior / blockers: live site not yet redeployed; awaiting user
  confirmation before `./deploy.sh` (it force-pushes gh-pages).
- Incomplete edits / running processes: none.
- Next concrete action: run `./deploy.sh`, then verify
  https://advikar.github.io/coolequity/contracosta/app/guide.html#overview returns 200
  and renders; record deployed hashes here.

## Checkpoint — September 9, 2026 (Claude): UX round 2 + walk-time correction

- Active packet: layman-feedback UX pass (see UX_ROUND2.md) and the routed walk-time
  defect it surfaced. Acceptance: every feedback point addressed, no score/rank change,
  tests green on all three v2 branches.
- Owner/model and branch/head: Claude (Fable 5.1); contra-costa, bakersfield, san-ramon.
- Files: app/index.html, app/guide.html, tests/ui-contract.cjs, tests/test_data_pipeline.py,
  pipeline/04b_routed_access.py, pipeline/05_score.py, data/<slug>.geojson,
  data/overlays_<slug>.csv, reports/*; STATUS.md on bakersfield and san-ramon;
  UX_ROUND2.md on contra-costa (this checkout's STATUS/DATA_QUALITY/FEATURES carry
  uncommitted Codex edits and were left untouched).
- Commands run: 04b → 05 → 06 per city (max rank change 0), unittest (8 OK per branch),
  node tests/ui-contract.cjs (5 PASS groups per branch), browser checks on 127.0.0.1:8801-8803.
- Unverified: live site until the user pushes and runs ./deploy.sh from this checkout.
- Next: user pushes the three branches and deploys; then CE-02 docs reconciliation and
  back-porting the remaining pipeline fixes to contra-costa.

## Checkpoint — September 10, 2026 (Claude): live audit, back-port, docs reconciliation

- Packet: full live audit after the September 9 deploy, then CE-02 (README/chooser
  reconciliation), back-port of pipeline drift to contra-costa, CE-09 chooser, CE-10 record.
- Files: app/index.html (contrast, key-handler guard; all three branches), site/index.html,
  README.md (four branches), pipeline/02d, 03, 06, tests/test_data_pipeline.py (contra-costa),
  reports/* (audit regenerated), STATUS.md (bakersfield, san-ramon), UX_ROUND2.md.
- Commands: unittest 8 OK per branch; node tests/ui-contract.cjs 5 PASS groups per branch;
  06_audit_rebuild.py max rank change 0 per city; live checks in the browser (see UX_ROUND2.md
  audit record).
- Not done: FEATURES.md / DATA_QUALITY.md / STATUS.md on this checkout still carry uncommitted
  Codex notes and were not edited; the small-population-cell question needs a product decision.
- Next: user pushes four branches and deploys; then the user's own UI changes.

## Checkpoint — September 11, 2026 (Claude): UX round 3 (feedback follow-ups)

- Packet: the skipped item from the layman list (every section folds, not only
  Priority areas), Export & share as its own section, legend moved onto the map,
  Simple on entry, save-before-leaving prompt, export naming/status, plain CSV
  headers + guide column key. Same commit on contra-costa, bakersfield, san-ramon.
- Verified: node tests/ui-contract.cjs 5 PASS per branch; JSON scenario export →
  reload round-trip in the browser restores preset, planting share and selection
  (2,697 areas); leave prompt appears only when priorities or shares changed;
  folds remembered; mobile layout checked at 375px. Downloads cannot be observed in
  the sandboxed browser pane, so the file-save step is verified by code path only.
- Next: user pushes three branches and deploys; then the user's remaining UI notes.

## Replace this section at each implementation checkpoint

- Active packet and acceptance criteria:
- Owner/model and branch/head:
- Files and city branches changed:
- Completed changes and preserved decisions:
- Commands run and exact pass/fail summary:
- Unverified behavior / blockers:
- Incomplete edits / running processes:
- Next concrete action:
- Release state and source/deployed hashes (if relevant):

### Live release verified — September 8, 2026

The public Contra Costa site now serves source commit `96963b1` through generated gh-pages build `7c8e415`. Live map, guide HTML/CSS/JS, cooling directory, hex data and cooling-site data returned HTTP 200 and matched the committed source byte-for-byte. Browser verification confirmed the updated landing page and loaded statistics. This supersedes earlier unpublished-status notes for that source revision. No product behavior or other city source branch changed during this verification; no repeat deployment was needed.
