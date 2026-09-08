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
